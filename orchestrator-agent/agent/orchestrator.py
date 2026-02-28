import sys
import os
import importlib.util

# ---------------------------------------------------------------------------
# Resolve the prospect-agent directory by walking up from this file's location
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ORCHESTRATOR_AGENT_DIR = os.path.dirname(_THIS_DIR)  # orchestrator-agent/
_PROSPECT_AGENT_DIR = os.path.join(os.path.dirname(_ORCHESTRATOR_AGENT_DIR), "prospect-agent")
_OUTREACH_AGENT_DIR = os.path.join(os.path.dirname(_ORCHESTRATOR_AGENT_DIR), "outreach-agent")
_PROJECT_ROOT = os.path.dirname(_ORCHESTRATOR_AGENT_DIR)

# ---------------------------------------------------------------------------
# Orchestrator-agent's own schemas must take precedence over prospect-agent's.
# Insert orchestrator-agent dir first so `schemas.input` resolves to PipelineInput.
# ---------------------------------------------------------------------------
if _ORCHESTRATOR_AGENT_DIR not in sys.path:
    sys.path.insert(0, _ORCHESTRATOR_AGENT_DIR)

# ---------------------------------------------------------------------------
# Load prospect-agent modules by absolute path to avoid `agent` / `schemas`
# namespace collisions.
# ---------------------------------------------------------------------------

def _load_module_from_path(module_name: str, file_path: str):
    """Load a Python module from an absolute file path under a unique module name."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


# Load prospect-agent's schemas.input (ICPInput) under a private name
_prospect_input_mod = _load_module_from_path(
    "_prospect_agent.schemas.input",
    os.path.join(_PROSPECT_AGENT_DIR, "schemas", "input.py"),
)
ICPInput = _prospect_input_mod.ICPInput

# Load prospect-agent's tools/people_sheet under a private name
_people_sheet_mod = _load_module_from_path(
    "_prospect_agent.tools.people_sheet",
    os.path.join(_PROSPECT_AGENT_DIR, "tools", "people_sheet.py"),
)
get_existing_people = _people_sheet_mod.get_existing_people
filter_duplicates = _people_sheet_mod.filter_duplicates
append_people = _people_sheet_mod.append_people

# Load prospect-agent's agent.orchestrator (ProspectingAgent) under a private name.
# prospect-agent/agent/orchestrator.py does `from schemas.input import ICPInput` and
# `from agent.tracer import log_trace` at module level.  We must temporarily:
#   1. Put the prospect-agent on the front of sys.path so `schemas` resolves there.
#   2. Pre-register `schemas.input` and `agent.tracer` as the prospect-agent versions
#      so the bare `from schemas.input import ICPInput` picks up ICPInput, not PipelineInput.
# After loading we restore the original sys.modules entries.

_saved = {}
_keys_to_swap = ["schemas", "schemas.input", "agent", "agent.tracer",
                 "agent.exceptions", "schemas.output"]

for _k in _keys_to_swap:
    _saved[_k] = sys.modules.get(_k)

try:
    # Pre-register prospect-agent's schemas.input so the bare import resolves correctly
    sys.modules["schemas.input"] = _prospect_input_mod

    # Also load prospect-agent's other deps that prospect-agent/agent/orchestrator.py needs
    _prospect_output_mod = _load_module_from_path(
        "_prospect_agent.schemas.output",
        os.path.join(_PROSPECT_AGENT_DIR, "schemas", "output.py"),
    )
    sys.modules["schemas.output"] = _prospect_output_mod

    _prospect_tracer_mod = _load_module_from_path(
        "_prospect_agent.agent.tracer",
        os.path.join(_PROSPECT_AGENT_DIR, "agent", "tracer.py"),
    )
    sys.modules["agent.tracer"] = _prospect_tracer_mod

    _prospect_exceptions_mod = _load_module_from_path(
        "_prospect_agent.agent.exceptions",
        os.path.join(_PROSPECT_AGENT_DIR, "agent", "exceptions.py"),
    )
    sys.modules["agent.exceptions"] = _prospect_exceptions_mod

    # Now load ProspectingAgent — its bare imports will resolve via the swapped sys.modules
    _prospect_orchestrator_mod = _load_module_from_path(
        "_prospect_agent.agent.orchestrator",
        os.path.join(_PROSPECT_AGENT_DIR, "agent", "orchestrator.py"),
    )
    ProspectingAgent = _prospect_orchestrator_mod.ProspectingAgent
finally:
    # Restore sys.modules so orchestrator-agent's schemas take precedence again.
    # This runs even if any _load_module_from_path call raises an exception,
    # ensuring sys.modules is never left in a dirty state.
    for _k, _v in _saved.items():
        if _v is None:
            sys.modules.pop(_k, None)
        else:
            sys.modules[_k] = _v

# ---------------------------------------------------------------------------
# Orchestrator-agent's own schemas (PipelineInput, PipelineResult, StageResult)
# ---------------------------------------------------------------------------
from schemas.input import PipelineInput  # noqa: E402
from schemas.output import PipelineResult, StageResult  # noqa: E402
from agent.tracer import log_trace  # noqa: E402


class OrchestratorAgent:
    """Coordinates the AI SDR pipeline across sub-agents."""

    def run(self, pipeline_input: PipelineInput) -> PipelineResult:
        log_trace("orchestrator_start", {"stages": pipeline_input.stages})
        result = PipelineResult()
        new_person_ids: list = []

        if "prospect" in pipeline_input.stages:
            stage_result = self._run_prospect_stage(pipeline_input)
            new_person_ids = stage_result.new_person_ids
            result.stages.append(stage_result)

        if "outreach" in pipeline_input.stages:
            outreach_result = self._run_outreach_stage(new_person_ids)
            result.stages.append(outreach_result)

        log_trace("orchestrator_complete", {
            "stages": [s.stage for s in result.stages],
            "statuses": [s.status for s in result.stages],
        })
        return result

    def _run_prospect_stage(self, pipeline_input: PipelineInput) -> StageResult:
        log_trace("prospect_stage_start", {})
        try:
            icp = ICPInput(
                industry=pipeline_input.industry,
                company_size=pipeline_input.company_size,
                roles_to_target=pipeline_input.roles_to_target,
                pain_points=pipeline_input.pain_points,
                location=pipeline_input.location,
                num_companies=pipeline_input.num_companies,
                num_people_per_company=pipeline_input.num_people_per_company,
            )

            existing_people = get_existing_people()
            existing_emails = list(existing_people.keys())

            agent = ProspectingAgent()
            people_output = agent.run(icp, existing_emails=existing_emails)

            people_dicts = [p.model_dump() for p in people_output.people]
            duplicates_skipped = 0

            if pipeline_input.enable_post_deduplication:
                people_dicts, duplicates = filter_duplicates(people_dicts)
                duplicates_skipped = len(duplicates)

            new_ids = []
            if people_dicts:
                append_people(people_dicts, industry=pipeline_input.industry)
                new_ids = [p.get("id", "") for p in people_dicts]

            return StageResult(
                stage="prospect",
                status="completed",
                people_found=len(people_output.people),
                people_written=len(people_dicts),
                duplicates_skipped=duplicates_skipped,
                new_person_ids=new_ids,
            )
        except Exception as e:
            log_trace("prospect_stage_error", {"error": str(e)})
            return StageResult(stage="prospect", status="failed", error=str(e))

    def _run_outreach_stage(self, person_ids: list) -> StageResult:
        log_trace("outreach_stage_start", {})
        try:
            # Ensure project root is on sys.path so `from schemas.crm import …` resolves.
            if _PROJECT_ROOT not in sys.path:
                sys.path.insert(0, _PROJECT_ROOT)

            # Bare module names the outreach orchestrator uses at import time.
            _bare = [
                "agent.config", "agent.exceptions", "agent.results", "agent.tracer",
                "tools", "tools.tool", "tools.email_clients", "tools.email_prospects",
                "tools.schedule_demo", "tools.schedule_followup",
            ]
            _saved = {k: sys.modules.get(k) for k in _bare}

            try:
                def _load_outreach(relpath, bare_name):
                    mod = _load_module_from_path(
                        f"_outreach_agent.{bare_name}",
                        os.path.join(_OUTREACH_AGENT_DIR, relpath),
                    )
                    sys.modules[bare_name] = mod
                    return mod

                config_mod = _load_outreach("agent/config.py",            "agent.config")
                _load_outreach("agent/exceptions.py",        "agent.exceptions")
                _load_outreach("agent/results.py",           "agent.results")
                _load_outreach("agent/tracer.py",            "agent.tracer")
                _load_outreach("tools/tool.py",              "tools.tool")
                _load_outreach("tools/email_clients.py",     "tools.email_clients")
                _load_outreach("tools/email_prospects.py",   "tools.email_prospects")
                _load_outreach("tools/schedule_demo.py",     "tools.schedule_demo")
                _load_outreach("tools/schedule_followup.py", "tools.schedule_followup")

                outreach_orch_mod = _load_module_from_path(
                    "_outreach_agent.agent.orchestrator",
                    os.path.join(_OUTREACH_AGENT_DIR, "agent", "orchestrator.py"),
                )
                OutreachOrchestrator = outreach_orch_mod.OutreachOrchestrator
                OutreachAgentConfig  = config_mod.OutreachAgentConfig
            finally:
                for k, v in _saved.items():
                    if v is None:
                        sys.modules.pop(k, None)
                    else:
                        sys.modules[k] = v

            config = OutreachAgentConfig(
                spreadsheet_id=os.environ["GOOGLE_SHEET_ID"],
                credentials_file=os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"),
                token_file=os.getenv("GOOGLE_TOKEN_FILE", "token.pickle"),
                sender_email=os.environ["SENDER_EMAIL"],
                sender_name=os.getenv("SENDER_NAME", ""),
                company_name=os.getenv("COMPANY_NAME", ""),
                bcc_email=os.getenv("BCC_EMAIL") or None,
                calendar_timezone=os.getenv("CALENDAR_TIMEZONE", "America/Denver"),
                demo_duration_minutes=int(os.getenv("DEMO_DURATION_MINUTES", "60")),
                followup_duration_minutes=int(os.getenv("FOLLOWUP_DURATION_MINUTES", "30")),
                google_meet=os.getenv("GOOGLE_MEET", "true").lower() == "true",
                followup_days=int(os.getenv("FOLLOWUP_DAYS", "7")),
                client_checkin_days=int(os.getenv("CLIENT_CHECKIN_DAYS", "30")),
                dry_run=os.getenv("OUTREACH_DRY_RUN", "false").lower() == "true",
            )

            run_result = OutreachOrchestrator(config).run()
            emails_sent = sum(1 for e in run_result.emails_sent if e.success)

            return StageResult(
                stage="outreach",
                status="completed",
                people_written=emails_sent,
                error="; ".join(run_result.errors) if run_result.errors else None,
            )
        except Exception as e:
            log_trace("outreach_stage_error", {"error": str(e)})
            return StageResult(stage="outreach", status="failed", error=str(e))
