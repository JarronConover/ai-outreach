"""Supabase-backed CRUD for the Emails table.

Replaces the gspread implementation. All reads and writes now go through
the Supabase PostgREST client via api.db.get_db().
"""
from __future__ import annotations

import os
import sys
from typing import Optional

# Ensure project root is in sys.path so `api.*` resolves correctly.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from api.db import get_db  # noqa: E402


def get_existing_message_ids() -> set:
    """Return the set of Gmail message_ids already recorded in the Emails table."""
    db = get_db()
    res = db.table("emails").select("message_id").execute()
    return {row["message_id"] for row in res.data if row.get("message_id")}


def get_emails(status_filter=None) -> list:
    """Return all email records, optionally filtered by status."""
    db = get_db()
    q = db.table("emails").select("*").order("received_at", desc=True)
    if status_filter:
        q = q.eq("status", status_filter)
    return q.execute().data


def get_emails_needing_response() -> list:
    """Return emails with category=manual that still need a human response."""
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


def get_email_by_id(email_id: str) -> Optional[dict]:
    """Return a single email record by id, or None."""
    db = get_db()
    res = db.table("emails").select("*").eq("id", email_id).limit(1).execute()
    return res.data[0] if res.data else None


def append_email(email: dict) -> None:
    """Insert a single email row into Supabase."""
    db = get_db()
    # Convert empty strings to None for proper DB null handling
    clean = {k: (v if v != "" else None) for k, v in email.items()}
    db.table("emails").insert(clean).execute()


def update_email_status(
    email_id: str,
    status: str,
    response_action_id: Optional[str] = None,
) -> None:
    """Update the status (and optionally response_action_id) of an email record."""
    db = get_db()
    payload: dict = {"status": status}
    if response_action_id is not None:
        payload["response_action_id"] = response_action_id
    db.table("emails").update(payload).eq("id", email_id).execute()
