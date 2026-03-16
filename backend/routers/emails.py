import threading
from fastapi import APIRouter, HTTPException
from backend.db.crud import get_emails, get_emails_needing_response, update_email_status
from backend.services.jobs import _jobs, _make_job, run_inbox_job

router = APIRouter(tags=["emails"])


@router.get("/emails")
def list_emails():
    """Return all inbox emails from Supabase."""
    try:
        return get_emails()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inbox/needs-response")
def list_needs_response():
    """Return emails with category=manual that still need a human response."""
    try:
        return get_emails_needing_response()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/inbox/run", status_code=202)
def start_inbox_run():
    """Scan the Gmail inbox, categorise emails, and create pending reply actions."""
    job_id, _ = _make_job("inbox_scan")
    threading.Thread(target=run_inbox_job, args=(job_id,), daemon=True).start()
    return {"job_id": job_id, "status": "pending"}


@router.post("/inbox/emails/{email_id}/resolve", status_code=200)
def resolve_email(email_id: str):
    """Mark a manual email as resolved so it leaves the Needs Response list."""
    try:
        update_email_status(email_id, "ignored")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"resolved": email_id}
