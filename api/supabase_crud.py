"""
Supabase CRUD operations — single source of truth for all CRM data.

All agents (prospect-agent, outreach-agent, inbox-agent) read and write
through Supabase. This module is the shared API-layer interface.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from api.db import get_db


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
