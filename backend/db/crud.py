"""
Supabase CRUD — single source of truth for all CRM data.

All agents read/write through here. This is the shared API-layer interface.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from backend.db.client import get_db


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------

def get_people() -> list[dict]:
    """Return all people rows joined with their company name."""
    db = get_db()
    res = (
        db.table("people")
        .select("*, companies(name)")
        .order("created_at", desc=False)
        .execute()
    )
    rows = []
    for r in res.data:
        company = r.pop("companies", None) or {}
        r["company_name"] = company.get("name", "")
        rows.append(r)
    return rows


def get_people_by_email() -> dict[str, dict]:
    """Return a dict keyed by email for fast lookup."""
    return {p["email"]: p for p in get_people()}


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------

def get_companies() -> list[dict]:
    db = get_db()
    return db.table("companies").select("*").execute().data


def get_company_map() -> dict[str, str]:
    """Return {company_id: company_name} for display."""
    return {c["id"]: c["name"] for c in get_companies()}


# ---------------------------------------------------------------------------
# Demos
# ---------------------------------------------------------------------------

def get_demos() -> list[dict]:
    """Return all demos joined with person name and company name."""
    db = get_db()
    res = (
        db.table("demos")
        .select("*, people(name, email), companies(name)")
        .order("date", desc=False)
        .execute()
    )
    rows = []
    for r in res.data:
        person = r.pop("people", None) or {}
        company = r.pop("companies", None) or {}
        r["person_name"] = person.get("name", "")
        r["person_email"] = person.get("email", "")
        r["company_name"] = company.get("name", "")
        rows.append(r)
    return rows


# ---------------------------------------------------------------------------
# Insert helpers (manual add flow)
# ---------------------------------------------------------------------------

def insert_company(data: dict) -> dict:
    """Insert or upsert a single company. Returns the saved row."""
    import uuid as _uuid
    db = get_db()
    row = {
        "id": data.get("id") or str(_uuid.uuid4()),
        "name": data.get("name", ""),
        "website": data.get("website") or None,
        "industry": data.get("industry") or None,
        "address": data.get("address") or None,
        "city": data.get("city") or None,
        "state": data.get("state") or None,
        "zip": data.get("zip") or None,
        "phone": data.get("phone") or None,
        "employee_count": data.get("employee_count") or None,
    }
    db.table("companies").upsert(row, on_conflict="id").execute()
    return row


def insert_person(data: dict) -> dict:
    """Insert or upsert a single person. Resolves company_id from company_name if needed."""
    import uuid as _uuid
    db = get_db()

    company_id = data.get("company_id")
    if not company_id and data.get("company_name"):
        company_name = data["company_name"].strip()
        res = db.table("companies").select("id").ilike("name", company_name).limit(1).execute()
        if res.data:
            company_id = res.data[0]["id"]
        else:
            company_id = str(_uuid.uuid4())
            db.table("companies").insert({"id": company_id, "name": company_name}).execute()

    row = {
        "id": data.get("id") or str(_uuid.uuid4()),
        "name": data.get("name", ""),
        "email": data.get("email", ""),
        "company_id": company_id or None,
        "phone": data.get("phone") or None,
        "linkedin": data.get("linkedin") or None,
        "title": data.get("title") or None,
        "stage": data.get("stage") or "prospect",
        "last_response": data.get("last_response") or None,
        "last_contact": data.get("last_contact") or None,
    }
    db.table("people").upsert(row, on_conflict="email").execute()
    return row


def insert_demo(data: dict) -> dict:
    """Insert a new demo record. Returns the saved row."""
    import uuid as _uuid
    db = get_db()
    row = {
        "id": data.get("id") or str(_uuid.uuid4()),
        "people_id": data.get("people_id") or None,
        "company_id": data.get("company_id") or None,
        "type": data.get("type") or "discovery",
        "date": data.get("date") or None,
        "status": data.get("status") or "scheduled",
        "count": data.get("count") or None,
        "event_id": data.get("event_id") or None,
    }
    db.table("demos").insert(row).execute()
    return row


def insert_email_record(data: dict) -> dict:
    """Insert a new inbox email record. Returns the saved row."""
    import uuid as _uuid
    from datetime import datetime, timezone
    db = get_db()
    row = {
        "id": data.get("id") or str(_uuid.uuid4()),
        "message_id": data.get("message_id") or str(_uuid.uuid4()),
        "from_email": data.get("from_email", ""),
        "from_name": data.get("from_name") or None,
        "people_id": data.get("people_id") or None,
        "subject": data.get("subject") or "",
        "body_snippet": data.get("body_snippet") or "",
        "received_at": data.get("received_at") or datetime.now(timezone.utc).isoformat(),
        "category": data.get("category") or "manual",
        "status": data.get("status") or "new",
        "note": data.get("note") or None,
    }
    db.table("emails").insert(row).execute()
    return row


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def get_actions(status: Optional[str] = None) -> list[dict]:
    """Return actions, optionally filtered by status."""
    db = get_db()
    q = db.table("actions").select("*").order("created_at", desc=False)
    if status:
        q = q.eq("status", status)
    return q.execute().data


def get_pending_actions() -> list[dict]:
    return get_actions(status="pending")


def get_action_by_id(action_id: str) -> Optional[dict]:
    db = get_db()
    res = db.table("actions").select("*").eq("id", action_id).limit(1).execute()
    return res.data[0] if res.data else None


def write_actions(action_dicts: list[dict]) -> None:
    """Insert new pending actions."""
    if not action_dicts:
        return
    db = get_db()
    db.table("actions").insert(action_dicts).execute()


def update_action_status(
    action_id: str,
    status: str,
    confirmed_at: Optional[str] = None,
) -> None:
    db = get_db()
    payload: dict = {"status": status}
    if confirmed_at:
        payload["confirmed_at"] = confirmed_at
    db.table("actions").update(payload).eq("id", action_id).execute()


def batch_update_action_status(
    action_ids: list[str],
    status: str,
    confirmed_at: Optional[str] = None,
) -> None:
    if not action_ids:
        return
    db = get_db()
    payload: dict = {"status": status}
    if confirmed_at:
        payload["confirmed_at"] = confirmed_at
    db.table("actions").update(payload).in_("id", action_ids).execute()


def cancel_pending_actions() -> None:
    """Cancel all currently pending actions."""
    db = get_db()
    db.table("actions").update({"status": "canceled"}).eq("status", "pending").execute()


def delete_pending_actions() -> None:
    """Delete all pending/confirming actions (called before writing a fresh plan)."""
    db = get_db()
    db.table("actions").delete().in_("status", ["pending", "confirming"]).execute()


# ---------------------------------------------------------------------------
# Emails (inbox)
# ---------------------------------------------------------------------------

def get_emails() -> list[dict]:
    """Return all inbox emails joined with person name."""
    db = get_db()
    res = (
        db.table("emails")
        .select("*, people(name)")
        .order("received_at", desc=True)
        .execute()
    )
    rows = []
    for r in res.data:
        person = r.pop("people", None) or {}
        r["person_name"] = person.get("name", "")
        rows.append(r)
    return rows


def get_emails_needing_response() -> list[dict]:
    """Return manual-category emails that still need a human response."""
    db = get_db()
    res = (
        db.table("emails")
        .select("*, people(name, email)")
        .eq("category", "manual")
        .in_("status", ["new", "pending_response"])
        .order("received_at", desc=True)
        .execute()
    )
    rows = []
    for r in res.data:
        person = r.pop("people", None) or {}
        r["person_name"] = person.get("name", "")
        r["person_email"] = person.get("email", "")
        rows.append(r)
    return rows


def update_email_status(
    email_id: str,
    status: str,
    response_action_id: Optional[str] = None,
) -> None:
    db = get_db()
    payload: dict = {"status": status}
    if response_action_id:
        payload["response_action_id"] = response_action_id
    db.table("emails").update(payload).eq("id", email_id).execute()


# ---------------------------------------------------------------------------
# Stats (derived from DB)
# ---------------------------------------------------------------------------

def get_stats() -> dict:
    """Compute KPI counts from Supabase."""
    people = get_people()
    demos = get_demos()

    stages = [p.get("stage", "").lower() for p in people]
    demo_statuses = [d.get("status", "").lower() for d in demos]

    client_stages = {"client", "onboarding", "pricing", "demo_completed", "demo_scheduled"}

    return {
        "total_prospects": len(stages),
        "clients": sum(1 for s in stages if s in client_stages),
        "demos_scheduled": sum(1 for s in demo_statuses if s == "scheduled"),
        "demos_completed": sum(1 for s in demo_statuses if s == "completed"),
    }


# ---------------------------------------------------------------------------
# Delete helpers
# ---------------------------------------------------------------------------

def get_demo_by_id(demo_id: str) -> Optional[dict]:
    db = get_db()
    res = db.table("demos").select("*").eq("id", demo_id).limit(1).execute()
    return res.data[0] if res.data else None


def delete_person(person_id: str) -> None:
    db = get_db()
    db.table("people").delete().eq("id", person_id).execute()


def delete_company(company_id: str) -> None:
    db = get_db()
    db.table("companies").delete().eq("id", company_id).execute()


def delete_demo(demo_id: str) -> None:
    db = get_db()
    db.table("demos").delete().eq("id", demo_id).execute()
