import time
from fastapi import APIRouter, HTTPException
from backend.db.crud import get_people, get_demos, get_stats, get_companies
from backend.services.jobs import _dashboard_cache

router = APIRouter(tags=["dashboard"])

_DASHBOARD_TTL = 30  # seconds


@router.get("/dashboard")
def get_dashboard():
    """Single endpoint returning people, demos, companies, and stats. Cached for 30s."""
    now = time.time()
    if _dashboard_cache["data"] is not None and now < _dashboard_cache["expires_at"]:
        return _dashboard_cache["data"]

    try:
        people = get_people()
        demos = get_demos()
        companies = get_companies()
        stats = get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    result = {"stats": stats, "people": people, "demos": demos, "companies": companies}
    _dashboard_cache["data"] = result
    _dashboard_cache["expires_at"] = now + _DASHBOARD_TTL
    return result


@router.get("/stats")
def stats_endpoint():
    """Return KPI counts from Supabase."""
    try:
        return get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
