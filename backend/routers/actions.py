import threading
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from backend.db.crud import (
    get_actions,
    get_action_by_id,
    update_action_status,
    batch_update_action_status,
    cancel_pending_actions,
)
from backend.services.jobs import _jobs, _make_job, run_single_action_job, run_all_actions_job, start_outreach_job

router = APIRouter(tags=["actions"])


@router.post("/outreach/plan", status_code=202)
def start_outreach_plan():
    """Run a dry-run preview; populates pending actions. Returns a job_id to poll."""
    job_id = start_outreach_job()
    return {"job_id": job_id, "status": "pending"}


@router.get("/outreach/pending")
def list_pending_actions():
    """Return all non-canceled outreach actions for the current plan batch."""
    try:
        actions = get_actions()
        return [a for a in actions if a["status"] != "canceled"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# confirm-all must be registered BEFORE /{action_id}/confirm to avoid routing conflict
@router.post("/outreach/pending/confirm-all", status_code=202)
def confirm_all_pending():
    """Execute all still-pending outreach actions."""
    try:
        pending = get_actions(status="pending")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    pending_ids = [a["id"] for a in pending]
    if not pending_ids:
        return {"message": "No pending actions to confirm", "job_id": None}
    try:
        batch_update_action_status(pending_ids, "confirming")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    job_id, _ = _make_job("outreach_confirm_all")
    threading.Thread(target=run_all_actions_job, args=(job_id, pending_ids), daemon=True).start()
    return {"job_id": job_id, "status": "pending", "actions": len(pending_ids)}


@router.delete("/outreach/pending")
def cancel_all_pending():
    """Cancel all pending outreach actions."""
    try:
        pending = get_actions(status="pending")
        count = len(pending)
        cancel_pending_actions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"cancelled": count}


@router.post("/outreach/pending/{action_id}/confirm", status_code=202)
def confirm_pending_action(action_id: str):
    """Execute a single pending outreach action."""
    try:
        action = get_action_by_id(action_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Action is already {action['status']}")
    try:
        update_action_status(action_id, "confirming")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    job_id, _ = _make_job("outreach_confirm_one")
    threading.Thread(target=run_single_action_job, args=(job_id, action), daemon=True).start()
    return {"job_id": job_id, "status": "pending"}


@router.post("/outreach/pending/{action_id}/compose", status_code=200)
def compose_email_action(action_id: str):
    """Mark an email action confirmed without auto-sending; user composes in Gmail."""
    try:
        action = get_action_by_id(action_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Action is already {action['status']}")
    try:
        update_action_status(action_id, "confirmed", datetime.now(timezone.utc).isoformat())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"confirmed": action_id}


@router.delete("/outreach/pending/{action_id}")
def cancel_pending_action(action_id: str):
    """Cancel a single pending outreach action."""
    try:
        action = get_action_by_id(action_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    try:
        update_action_status(action_id, "canceled")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"cancelled": action_id}
