import os
import pickle

from fastapi import APIRouter, HTTPException
from backend.db.crud import get_demos, get_demo_by_id, delete_demo

router = APIRouter(tags=["demos"])

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_OUTREACH_AGENT_DIR = os.path.join(_PROJECT_ROOT, "outreach-agent")


def _try_delete_calendar_event(event_id: str) -> None:
    """Best-effort: delete a Google Calendar event without notifying attendees."""
    try:
        from googleapiclient.discovery import build  # type: ignore

        token_file = os.getenv(
            "GOOGLE_TOKEN_FILE",
            os.path.join(_OUTREACH_AGENT_DIR, "token.pickle"),
        )
        with open(token_file, "rb") as f:
            creds = pickle.load(f)

        service = build("calendar", "v3", credentials=creds)
        service.events().delete(
            calendarId="primary",
            eventId=event_id,
            sendUpdates="none",
        ).execute()
    except Exception:
        pass  # Best-effort — don't block demo deletion if calendar call fails


@router.get("/demos")
def list_demos():
    """Return all demos enriched with person and company names."""
    try:
        demos = get_demos()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    demos.sort(key=lambda d: (d.get("date") or ""))
    return demos


@router.delete("/demos/{demo_id}", status_code=204)
def delete_demo_endpoint(demo_id: str):
    """Delete a demo and its associated Google Calendar event (no attendee notification)."""
    try:
        demo = get_demo_by_id(demo_id)
        if not demo:
            raise HTTPException(status_code=404, detail="Demo not found")
        event_id = demo.get("event_id")
        if event_id:
            _try_delete_calendar_event(event_id)
        delete_demo(demo_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
