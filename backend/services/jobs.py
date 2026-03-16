"""
In-memory job store and all background job thread functions.

Routers import helpers from here to enqueue or query jobs.
"""
from __future__ import annotations

import os
import uuid
import threading
from datetime import datetime
from typing import Optional

from backend.services.agent_loader import (
    ProspectingAgent,
    OrchestratorAgent,
    PipelineInput,
    log_trace,
    append_people,
    filter_duplicates,
    get_existing_people,
    _import_from,
    _INBOX_AGENT_DIR,
)
from backend.db.crud import (
    get_actions,
    get_action_by_id,
    write_actions,
    update_action_status,
    batch_update_action_status,
    delete_pending_actions,
)

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

_jobs: dict[str, dict] = {}
_dashboard_cache: dict = {"data": None, "expires_at": 0.0}
_orchestrator_job_id: Optional[str] = None
_orchestrator_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_job(job_type: str) -> tuple[str, dict]:
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "status": "pending",
        "type": job_type,
        "created_at": datetime.utcnow().isoformat(),
    }
    _jobs[job_id] = job
    return job_id, job


def start_outreach_job() -> str:
    """Enqueue an outreach plan job that creates pending actions."""
    job_id, _ = _make_job("outreach_plan")
    threading.Thread(target=run_outreach_plan_job, args=(job_id,), daemon=True).start()
    return job_id


# ---------------------------------------------------------------------------
# Job runners
# ---------------------------------------------------------------------------

def run_prospect_job(job_id: str, icp, enable_post_dedup: bool, industry: str = ""):
    _jobs[job_id]["status"] = "running"
    _jobs[job_id]["started_at"] = datetime.utcnow().isoformat()
    try:
        existing_people = get_existing_people()
        existing_emails = list(existing_people.keys())

        agent = ProspectingAgent()
        people_output = agent.run(icp, existing_emails=existing_emails)

        log_trace("writing_to_supabase", {"people_count": len(people_output.people)})
        people_dicts = [p.model_dump() for p in people_output.people]

        duplicates_skipped = 0
        if enable_post_dedup:
            people_dicts, duplicates = filter_duplicates(people_dicts)
            duplicates_skipped = len(duplicates)

        if people_dicts:
            append_people(people_dicts, industry=industry)
            start_outreach_job()

        _dashboard_cache["expires_at"] = 0.0

        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
        _jobs[job_id]["result"] = {
            "people_found": len(people_output.people),
            "people_written": len(people_dicts),
            "duplicates_skipped": duplicates_skipped,
            "people": [
                {
                    "name": p.name,
                    "title": p.title,
                    "company": p.company_id,
                    "email": p.email,
                    "linkedin": p.linkedin,
                }
                for p in people_output.people
            ],
        }
    except Exception as e:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)
        _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()


def run_pipeline_job(job_id: str, pipeline_input: PipelineInput):
    _jobs[job_id]["status"] = "running"
    _jobs[job_id]["started_at"] = datetime.utcnow().isoformat()
    try:
        agent = OrchestratorAgent()
        result = agent.run(pipeline_input)

        prospect_stage = next((s for s in result.stages if s.stage == "prospect"), None)
        if prospect_stage and prospect_stage.people_written:
            start_outreach_job()
            _dashboard_cache["expires_at"] = 0.0

        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
        _jobs[job_id]["result"] = result.model_dump()
    except Exception as e:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)
        _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()


def run_outreach_plan_job(job_id: str):
    """Dry-run the outreach plan and write pending actions to Supabase."""
    _jobs[job_id]["status"] = "running"
    _jobs[job_id]["started_at"] = datetime.utcnow().isoformat()
    try:
        plan = OrchestratorAgent().plan_outreach()

        delete_pending_actions()
        now = datetime.utcnow().isoformat()
        new_actions = []

        for e in plan.emails_sent:
            if not e.success or e.email_type == "demo_invite":
                continue
            new_actions.append({
                "id": str(uuid.uuid4()),
                "kind": "email",
                "email_type": e.email_type,
                "recipient_email": e.recipient_email,
                "recipient_name": e.recipient_name,
                "subject": e.subject,
                "body": e.body or "",
                "people_id": e.person_id,
                "status": "pending",
                "created_at": now,
            })

        for c in plan.calendar_events_created:
            if not c.success:
                continue
            new_actions.append({
                "id": str(uuid.uuid4()),
                "kind": "calendar",
                "event_type": c.event_type,
                "event_title": c.event_title,
                "attendees": c.attendees,
                "start_time": c.start_time.isoformat() if c.start_time else None,
                "end_time": c.end_time.isoformat() if c.end_time else None,
                "demo_id": c.demo_id,
                "status": "pending",
                "created_at": now,
            })

        write_actions(new_actions)
        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
        _jobs[job_id]["result"] = {"pending_actions": len(new_actions)}
        print(f"[outreach_plan] completed — {len(new_actions)} action(s) written", flush=True)
    except Exception as e:
        print(f"[outreach_plan] FAILED: {e}", flush=True)
        import traceback; traceback.print_exc()
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)
        _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()


def run_inbox_job(job_id: str):
    """Scan Gmail inbox, categorise emails, and create pending reply actions."""
    _jobs[job_id]["status"] = "running"
    _jobs[job_id]["started_at"] = datetime.utcnow().isoformat()
    try:
        _inbox_orch_mod = _import_from(
            os.path.join(_INBOX_AGENT_DIR, "agent", "orchestrator.py"),
            "_api.ia.agent.orchestrator",
        )
        _inbox_config_mod = _import_from(
            os.path.join(_INBOX_AGENT_DIR, "agent", "config.py"),
            "_api.ia.agent.config",
        )
        InboxOrchestrator = _inbox_orch_mod.InboxOrchestrator
        InboxAgentConfig = _inbox_config_mod.InboxAgentConfig

        config = InboxAgentConfig.from_env()
        result = InboxOrchestrator(config).run()

        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
        _jobs[job_id]["result"] = {
            "emails_processed": result.total,
            "actions_created": result.actions_created,
            "manual_count": result.manual_count,
            "skipped": result.skipped,
            "errors": result.errors,
        }
        print(
            f"[inbox_job] completed — {result.total} emails, "
            f"{result.actions_created} actions, {result.manual_count} manual",
            flush=True,
        )
    except Exception as e:
        import traceback; traceback.print_exc()
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)
        _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()


def run_single_action_job(job_id: str, action: dict):
    _jobs[job_id]["status"] = "running"
    _jobs[job_id]["started_at"] = datetime.utcnow().isoformat()
    action_id = action["id"]
    try:
        OrchestratorAgent().execute_confirmed_actions([action])
        update_action_status(action_id, "confirmed", datetime.utcnow().isoformat())
        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
    except Exception as e:
        try:
            update_action_status(action_id, "pending")
        except Exception:
            pass
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)
        _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()


def run_enrich_and_add_job(job_id: str, entity_type: str, partial_data: dict):
    """Enrich a partial entity via the prospect agent and write to Supabase."""
    _jobs[job_id]["status"] = "running"
    _jobs[job_id]["started_at"] = datetime.utcnow().isoformat()
    try:
        result = OrchestratorAgent().enrich_and_add_entity(entity_type, partial_data)
        _dashboard_cache["expires_at"] = 0.0
        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
        _jobs[job_id]["result"] = result
        print(f"[enrich_add] completed — {entity_type} enriched and saved", flush=True)
    except Exception as e:
        import traceback; traceback.print_exc()
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)
        _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()


def run_all_actions_job(job_id: str, action_ids: list):
    _jobs[job_id]["status"] = "running"
    _jobs[job_id]["started_at"] = datetime.utcnow().isoformat()
    try:
        all_actions = get_actions()
        id_set = set(action_ids)
        actions = [a for a in all_actions if a["id"] in id_set]
        OrchestratorAgent().execute_confirmed_actions(actions)
        now = datetime.utcnow().isoformat()
        batch_update_action_status(action_ids, "confirmed", now)
        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
    except Exception as e:
        try:
            batch_update_action_status(action_ids, "pending")
        except Exception:
            pass
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)
        _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
