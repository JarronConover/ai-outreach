"""
Manual add endpoints — allows adding individual people, companies, demos, and emails.

If all key fields are provided, the entity is inserted directly into Supabase.
If fields are missing (and enrichment is possible), the record is sent to the
orchestrator agent which calls the prospect agent to find missing info first.
"""
from __future__ import annotations

import threading
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.db.crud import insert_company, insert_person, insert_demo, insert_email_record
from backend.services.jobs import _make_job, _jobs, run_enrich_and_add_job

router = APIRouter(prefix="/add", tags=["add"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class AddPersonRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    company_name: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    stage: Optional[str] = "prospect"


class AddCompanyRequest(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    phone: Optional[str] = None
    employee_count: Optional[int] = None


class AddDemoRequest(BaseModel):
    people_id: Optional[str] = None
    company_id: Optional[str] = None
    type: Optional[str] = "discovery"
    date: Optional[str] = None
    status: Optional[str] = "scheduled"


class AddEmailRequest(BaseModel):
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    subject: Optional[str] = None
    body_snippet: Optional[str] = None
    category: Optional[str] = "manual"
    note: Optional[str] = None
    people_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _at_least_one(data: dict) -> bool:
    """Return True if at least one value in the dict is non-empty."""
    return any(v not in (None, "", []) for v in data.values())


def _person_needs_enrichment(req: AddPersonRequest) -> bool:
    """Person needs enrichment if email is missing OR both title and linkedin are missing."""
    if not req.email:
        return True
    if not req.title and not req.linkedin:
        return True
    return False


def _company_needs_enrichment(req: AddCompanyRequest) -> bool:
    """Company needs enrichment if website OR industry is missing."""
    if not req.website or not req.industry:
        return True
    return False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/person")
def add_person(req: AddPersonRequest):
    data = req.model_dump(exclude_none=True)
    if not _at_least_one(data):
        raise HTTPException(status_code=400, detail="At least one field is required.")

    if _person_needs_enrichment(req):
        # Enrich via orchestrator → prospect agent
        job_id, _ = _make_job("enrich_add_person")
        threading.Thread(
            target=run_enrich_and_add_job,
            args=(job_id, "person", data),
            daemon=True,
        ).start()
        return {"job_id": job_id, "enriching": True}

    # All key fields provided — insert directly
    saved = insert_person(data)
    return {"enriching": False, "entity": saved}


@router.post("/company")
def add_company(req: AddCompanyRequest):
    data = req.model_dump(exclude_none=True)
    if not _at_least_one(data):
        raise HTTPException(status_code=400, detail="At least one field is required.")

    if _company_needs_enrichment(req):
        job_id, _ = _make_job("enrich_add_company")
        threading.Thread(
            target=run_enrich_and_add_job,
            args=(job_id, "company", data),
            daemon=True,
        ).start()
        return {"job_id": job_id, "enriching": True}

    saved = insert_company(data)
    return {"enriching": False, "entity": saved}


@router.post("/demo")
def add_demo(req: AddDemoRequest):
    data = req.model_dump(exclude_none=True)
    if not _at_least_one(data):
        raise HTTPException(status_code=400, detail="At least one field is required.")

    # Demos are not enrichable — insert directly
    saved = insert_demo(data)
    return {"enriching": False, "entity": saved}


@router.post("/email")
def add_email(req: AddEmailRequest):
    data = req.model_dump(exclude_none=True)
    if not _at_least_one(data):
        raise HTTPException(status_code=400, detail="At least one field is required.")

    # Emails are not enrichable — insert directly
    saved = insert_email_record(data)
    return {"enriching": False, "entity": saved}
