import sys
import os
import importlib.util

# ---------------------------------------------------------------------------
# Resolve the prospect-agent directory by walking up from this file's location
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ORCHESTRATOR_AGENT_DIR = os.path.dirname(_THIS_DIR)  # orchestrator-agent/
_PROJECT_ROOT = os.path.dirname(_ORCHESTRATOR_AGENT_DIR)
_PROSPECT_AGENT_DIR = os.path.join(_PROJECT_ROOT, "prospect-agent")
_OUTREACH_AGENT_DIR = os.path.join(_PROJECT_ROOT, "outreach-agent")
_INBOX_AGENT_DIR = os.path.join(_PROJECT_ROOT, "inbox-agent")

# Module keys that belong exclusively to the outreach-agent; saved/restored around dynamic loads
_OA_MODULE_KEYS = [
    "agent", "agent.config", "agent.orchestrator", "agent.tracer",
    "agent.exceptions", "agent.results",
    "tools", "tools.tool", "tools.email_clients", "tools.email_prospects",
    "tools.schedule_demo", "tools.schedule_followup",
]

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
get_company_names = _people_sheet_mod.get_company_names
filter_duplicates = _people_sheet_mod.filter_duplicates
append_people = _people_sheet_mod.append_people
append_company = _people_sheet_mod.append_company

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
            existing_companies = list(get_company_names().values())

            agent = ProspectingAgent()
            people_output = agent.run(icp, existing_emails=existing_emails, existing_companies=existing_companies)

            people_dicts = [p.model_dump() for p in people_output.people]
            companies_by_name = {
                c.name.lower(): c.model_dump()
                for c in (people_output.companies or [])
            }
            duplicates_skipped = 0

            if pipeline_input.enable_post_deduplication:
                people_dicts, duplicates = filter_duplicates(people_dicts)
                duplicates_skipped = len(duplicates)

            new_ids = []
            if people_dicts:
                append_people(people_dicts, industry=pipeline_input.industry, companies_by_name=companies_by_name)
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
        log_trace("outreach_stage_skipped", {"person_ids": person_ids, "reason": "not yet implemented"})
        return StageResult(
            stage="outreach",
            status="skipped",
            error="OutreachAgent not yet available — merge outreach branch to enable.",
        )

    # ------------------------------------------------------------------
    # Entity enrichment & add
    # ------------------------------------------------------------------

    def enrich_and_add_entity(self, entity_type: str, partial_data: dict) -> dict:
        """Enrich a partial entity record via the prospect agent and write to Supabase.

        Args:
            entity_type: "person" or "company"
            partial_data: Whatever fields the user provided

        Returns:
            The enriched entity dict that was saved to Supabase
        """
        log_trace("enrich_and_add_start", {"entity_type": entity_type, "partial_data": partial_data})
        agent = ProspectingAgent()
        enriched = agent.enrich_entity(entity_type, partial_data)
        log_trace("enrich_and_add_enriched", {"entity_type": entity_type, "enriched": enriched})

        if entity_type == "person":
            append_people([enriched])
        elif entity_type == "company":
            enriched = append_company(enriched)

        log_trace("enrich_and_add_complete", {"entity_type": entity_type})
        return enriched

    # ------------------------------------------------------------------
    # Outreach-agent integration
    # ------------------------------------------------------------------

    def plan_outreach(self):
        """Run the outreach-agent in dry-run mode and return an OutreachRunResult."""
        return self._call_outreach(lambda orch: orch.plan())

    def execute_confirmed_actions(self, actions: list) -> None:
        """Execute a list of confirmed action dicts via the outreach-agent tools."""
        _INBOX_REPLY_TYPES = {
            "inbox_reply_interested",
            "inbox_reply_not_interested",
            "inbox_reply_demo_request",
        }

        # Separate inbox reply actions — handled directly, not via outreach tools.
        inbox_reply_actions = [
            a for a in actions
            if a.get("kind") == "email" and a.get("email_type") in _INBOX_REPLY_TYPES
        ]
        outreach_actions = [a for a in actions if a not in inbox_reply_actions]

        # --- Execute inbox replies ---
        if inbox_reply_actions:
            self._execute_inbox_replies(inbox_reply_actions)

        # --- Execute standard outreach actions ---
        if not outreach_actions:
            return

        def _execute(orch):
            crm = orch.api.load_crm_context()

            prospect_ids: set = set()
            client_ids: set = set()
            followup_ids: set = set()
            calendar_demo_ids: set = set()

            for action in outreach_actions:
                if action["kind"] == "email":
                    pid = action.get("people_id")
                    if not pid:
                        continue
                    etype = action.get("email_type", "")
                    if etype == "prospect_outreach":
                        prospect_ids.add(pid)
                    elif etype == "client_outreach":
                        client_ids.add(pid)
                    elif etype == "followup_email":
                        followup_ids.add(pid)
                elif action["kind"] == "calendar":
                    did = action.get("demo_id")
                    if did:
                        calendar_demo_ids.add(did)

            def _filter(person_ids, demo_ids):
                fp = [p for p in crm.people if p.id in person_ids]
                dp_ids = {d.people_id for d in crm.demos if d.id in demo_ids}
                for p in crm.people:
                    if p.id in dp_ids and p.id not in person_ids:
                        fp.append(p)
                fd = [d for d in crm.demos if d.id in demo_ids or d.people_id in person_ids]
                return crm.__class__(people=fp, companies=crm.companies, demos=fd)

            if prospect_ids:
                orch.email_prospects_tool.execute(_filter(prospect_ids, set()))
            if client_ids:
                orch.email_clients_tool.execute(_filter(client_ids, set()))
            if followup_ids:
                orch.schedule_followup_tool.execute(_filter(followup_ids, set()))
            if calendar_demo_ids:
                orch.schedule_demo_tool.execute(_filter(set(), calendar_demo_ids))

        self._call_outreach(_execute)

    def _execute_inbox_replies(self, actions: list) -> None:
        """
        Send inbox reply emails, refining each draft body with the stored note
        before sending (uses Gemini via email_categorizer.refine_reply).
        """
        import re as _re

        # Load emails_sheet and refine_reply from inbox-agent by absolute path
        _ia_emails_mod = _load_module_from_path(
            "_ia_emails_sheet",
            os.path.join(_INBOX_AGENT_DIR, "tools", "emails_sheet.py"),
        )
        get_email_by_id = _ia_emails_mod.get_email_by_id

        _ia_cat_mod = _load_module_from_path(
            "_ia_email_categorizer",
            os.path.join(_INBOX_AGENT_DIR, "tools", "email_categorizer.py"),
        )
        refine_reply = _ia_cat_mod.refine_reply

        sender_name = os.getenv("SENDER_NAME", "")
        our_company = os.getenv("COMPANY_NAME", "Fellowship")

        # Refine bodies using stored notes before entering the outreach context
        refined_actions = []
        for action in actions:
            body = action.get("body", "")
            source_email_id = action.get("source_email_id", "")
            note = ""
            if source_email_id:
                try:
                    email_record = get_email_by_id(source_email_id)
                    if email_record:
                        note = email_record.get("note", "") or ""
                except Exception as exc:
                    print(f"[inbox_reply] could not load note for action {action.get('id')}: {exc}")

            if note and body:
                try:
                    body = refine_reply(
                        draft_body=body,
                        note=note,
                        recipient_name=action.get("recipient_name", ""),
                        sender_name=sender_name,
                        our_company=our_company,
                    )
                    print(f"[inbox_reply] refined reply for {action.get('recipient_email')} using note")
                except Exception as exc:
                    print(f"[inbox_reply] refine failed for action {action.get('id')}: {exc}")

            refined_actions.append({**action, "body": body})

        def _send_replies(orch):
            sender = f"{orch.config.sender_name} <{orch.config.sender_email}>"
            for action in refined_actions:
                to = action.get("recipient_email", "")
                subject = action.get("subject", "")
                body = action.get("body", "")
                if not to or not body:
                    print(f"[inbox_reply] skipping action {action.get('id')} — missing to/body")
                    continue
                plain = body.replace("<br>", "\n").replace("</p>", "\n")
                plain = _re.sub(r"<[^>]+>", "", plain).strip()
                orch.api.send_email(
                    sender=sender,
                    to=to,
                    subject=subject,
                    html_body=body,
                    plain_body=plain,
                )
                print(f"[inbox_reply] sent reply to {to} | subject={subject!r}")

        self._call_outreach(_send_replies)

    def _call_outreach(self, fn):
        """
        Temporarily load the outreach-agent into sys.path/sys.modules, build an
        OutreachOrchestrator, call fn(orchestrator), then restore the module state.
        """
        # Save/clear all module keys used by the outreach-agent plus the `schemas`
        # package entries.  We must also temporarily remove _ORCHESTRATOR_AGENT_DIR
        # from sys.path because it has its own schemas/ subdirectory that would
        # shadow the project root's schemas/crm.py when those modules are re-imported.
        _schema_keys = [
            "schemas", "schemas.crm", "schemas.sheet_config",
            "schemas.input", "schemas.output",
        ]
        _all_keys = _OA_MODULE_KEYS + _schema_keys
        saved = {k: sys.modules.get(k) for k in _all_keys}
        _added_outreach = _OUTREACH_AGENT_DIR not in sys.path
        try:
            for k in _all_keys:
                sys.modules.pop(k, None)
            if _added_outreach:
                sys.path.insert(0, _OUTREACH_AGENT_DIR)

            # Pre-register the project root's schemas package directly so that
            # outreach-agent tools can do `from schemas.crm import ...` regardless
            # of which schemas/ directory sys.path resolves to.
            _schemas_spec = importlib.util.spec_from_file_location(
                "schemas",
                os.path.join(_PROJECT_ROOT, "schemas", "__init__.py"),
                submodule_search_locations=[os.path.join(_PROJECT_ROOT, "schemas")],
            )
            _schemas_mod = importlib.util.module_from_spec(_schemas_spec)
            sys.modules["schemas"] = _schemas_mod
            _schemas_spec.loader.exec_module(_schemas_mod)

            _load_module_from_path(
                "schemas.crm",
                os.path.join(_PROJECT_ROOT, "schemas", "crm.py"),
            )
            _load_module_from_path(
                "schemas.sheet_config",
                os.path.join(_PROJECT_ROOT, "schemas", "sheet_config.py"),
            )

            from agent.config import OutreachAgentConfig   # noqa: E402
            from agent.orchestrator import OutreachOrchestrator  # noqa: E402

            missing = [
                v for v in ("SENDER_EMAIL", "SENDER_NAME", "COMPANY_NAME")
                if not os.getenv(v)
            ]
            if missing:
                raise RuntimeError(f"Missing env vars: {', '.join(missing)}")

            config = OutreachAgentConfig(
                credentials_file=os.getenv(
                    "GOOGLE_CREDENTIALS_FILE",
                    os.path.join(_OUTREACH_AGENT_DIR, "credentials.json"),
                ),
                token_file=os.getenv(
                    "GOOGLE_TOKEN_FILE",
                    os.path.join(_OUTREACH_AGENT_DIR, "token.pickle"),
                ),
                sender_email=os.environ["SENDER_EMAIL"],
                sender_name=os.environ["SENDER_NAME"],
                company_name=os.environ["COMPANY_NAME"],
                bcc_email=os.getenv("BCC_EMAIL") or None,
                calendar_timezone=os.getenv("CALENDAR_TIMEZONE", "America/Denver"),
                demo_duration_minutes=int(os.getenv("DEMO_DURATION_MINUTES", "60")),
                followup_duration_minutes=int(os.getenv("FOLLOWUP_DURATION_MINUTES", "30")),
                google_meet=os.getenv("GOOGLE_MEET", "true").lower() == "true",
                followup_days=int(os.getenv("FOLLOWUP_DAYS", "7")),
                client_checkin_days=int(os.getenv("CLIENT_CHECKIN_DAYS", "30")),
                dry_run=False,
            )
            orch = OutreachOrchestrator(config)
            return fn(orch)
        finally:
            if _added_outreach:
                try:
                    sys.path.remove(_OUTREACH_AGENT_DIR)
                except ValueError:
                    pass
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
