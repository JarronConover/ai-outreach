import sys
import os
import importlib.util

# ---------------------------------------------------------------------------
# Resolve the prospect-agent directory by walking up from this file's location
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ORCHESTRATOR_AGENT_DIR = os.path.dirname(_THIS_DIR)  # orchestrator-agent/
_PROSPECT_AGENT_DIR = os.path.join(os.path.dirname(_ORCHESTRATOR_AGENT_DIR), "prospect-agent")

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

# Restore sys.modules so orchestrator-agent's schemas take precedence again
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
                append_people(people_dicts)
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
        """Stub: outreach agent is being developed on a separate branch.

        When OutreachAgent is merged, replace this body with:
            from outreach_agent.agent.orchestrator import OutreachAgent
            agent = OutreachAgent()
            agent.run(person_ids=person_ids)
        """
        log_trace("outreach_stage_skipped", {"person_ids": person_ids, "reason": "not yet implemented"})
        return StageResult(
            stage="outreach",
            status="skipped",
            error="OutreachAgent not yet available — merge outreach branch to enable.",
        )
