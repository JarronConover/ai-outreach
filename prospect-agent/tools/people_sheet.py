"""Supabase-backed CRUD for People and Companies data.

Replaces the previous gspread implementation. All reads and writes now
go through the Supabase PostgREST client via api.db.get_db().
"""
import os
import sys
import uuid
from typing import List, Optional

# Ensure project root is in sys.path so `api.*` resolves correctly.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from api.db import get_db  # noqa: E402


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def get_existing_people() -> dict:
    """Return all people keyed by lowercase email -> person dict.

    Compatible with the api/main.py sheet-poller which expects
    {email: record} where each record exposes 'id' and 'last_contact'.
    """
    db = get_db()
    res = (
        db.table("people")
        .select("id, name, email, last_contact, last_contact_date, stage")
        .execute()
    )
    return {
        row["email"].lower(): row
        for row in res.data
        if row.get("email")
    }


def get_people_dicts() -> list:
    """Return all people joined with company names."""
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


def get_company_names() -> dict:
    """Return {company_id: company_name}."""
    db = get_db()
    res = db.table("companies").select("id, name").execute()
    return {row["id"]: row["name"] for row in res.data}


def get_demos_dicts() -> list:
    """Return all demos joined with person and company names."""
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
# Deduplication
# ---------------------------------------------------------------------------


def filter_duplicates(new_people, industry=None):
    """Filter out people whose email already exists in Supabase."""
    existing = get_existing_people()
    filtered, duplicates = [], []
    for person in new_people:
        email = person.get("email", "").strip().lower()
        if email and email in existing:
            duplicates.append(email)
        else:
            filtered.append(person)
    return filtered, duplicates


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------


def append_people(people_list, industry=None, companies_by_name=None):
    """Upsert people (and their companies) into Supabase.

    For each person that carries a `company_name` field, the company is looked
    up by name (case-insensitive) or created if it does not yet exist, and the
    resulting UUID is set as the person's `company_id`.

    Args:
        people_list: List of person dicts to upsert.
        industry: Fallback industry string if not provided by company data.
        companies_by_name: Optional dict of {company_name_lower: company_dict} with
            full company details (website, city, state, zip, phone, employee_count, etc.)
            returned by the prospecting agent.
    """
    if not people_list:
        return "Success: 0 people added."

    db = get_db()
    _companies_by_name = {k.lower(): v for k, v in (companies_by_name or {}).items()}

    # Build name->id map from existing companies
    company_rows = db.table("companies").select("id, name").execute().data
    name_to_id = {row["name"].lower(): row["id"] for row in company_rows}

    # Resolve or create companies referenced by the new people
    new_companies = []
    seen_names = {}  # name.lower() -> uuid (for this batch)

    for person in people_list:
        company_name = (person.get("company_name") or "").strip()
        if not company_name:
            continue
        cn_lower = company_name.lower()
        if cn_lower in name_to_id:
            person["company_id"] = name_to_id[cn_lower]
        elif cn_lower in seen_names:
            person["company_id"] = seen_names[cn_lower]
        else:
            new_id = str(uuid.uuid4())
            seen_names[cn_lower] = new_id
            details = _companies_by_name.get(cn_lower, {})
            new_companies.append({
                "id": new_id,
                "name": company_name,
                "industry": details.get("industry") or industry or "",
                "website": details.get("website") or None,
                "address": details.get("address") or None,
                "city": details.get("city") or None,
                "state": details.get("state") or None,
                "zip": details.get("zip") or None,
                "phone": details.get("phone") or None,
                "employee_count": details.get("employee_count") or None,
            })
            person["company_id"] = new_id

    if new_companies:
        db.table("companies").upsert(new_companies, on_conflict="id").execute()

    # Build clean person rows
    person_rows = []
    for person in people_list:
        person_rows.append({
            "id": person.get("id") or str(uuid.uuid4()),
            "name": person.get("name", ""),
            "email": person.get("email", ""),
            "company_id": person.get("company_id") or None,
            "phone": person.get("phone") or None,
            "linkedin": person.get("linkedin") or None,
            "title": person.get("title") or None,
            "stage": person.get("stage") or "prospect",
            "last_response": person.get("last_response") or None,
            "last_contact": person.get("last_contact") or None,
            "last_response_date": person.get("last_response_date") or None,
            "last_contact_date": person.get("last_contact_date") or None,
        })

    db.table("people").upsert(person_rows, on_conflict="email").execute()
    return f"Success: added {len(person_rows)} people to Supabase."


def append_person(person_dict):
    """Insert or update a single person in Supabase."""
    return append_people([person_dict])


def append_company(company_dict: dict) -> dict:
    """Insert or update a single company in Supabase. Returns the saved company dict."""
    db = get_db()
    row = {
        "id": company_dict.get("id") or str(uuid.uuid4()),
        "name": company_dict.get("name", ""),
        "website": company_dict.get("website") or None,
        "industry": company_dict.get("industry") or None,
        "address": company_dict.get("address") or None,
        "city": company_dict.get("city") or None,
        "state": company_dict.get("state") or None,
        "zip": company_dict.get("zip") or None,
        "phone": company_dict.get("phone") or None,
        "employee_count": company_dict.get("employee_count") or None,
    }
    db.table("companies").upsert(row, on_conflict="id").execute()
    return row
