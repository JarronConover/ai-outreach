"""Read Demos from Supabase, enriched with person and company info.

Returns demo rows ready for the /demos API endpoint.
"""

from __future__ import annotations

import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from api.db import get_db  # noqa: E402


def get_demos() -> list[dict]:
    """Return all demo rows enriched with person and company info."""
    db = get_db()

    demos_res = db.table("demos").select("*, people(name, email), companies(name)").execute()

    result = []
    for row in demos_res.data:
        person = row.pop("people", None) or {}
        company = row.pop("companies", None) or {}
        result.append({
            "id": row.get("id", ""),
            "type": row.get("type", ""),
            "date": row.get("date"),
            "status": row.get("status", ""),
            "event_id": row.get("event_id") or None,
            "person_name": person.get("name", "Unknown"),
            "person_email": person.get("email"),
            "company_name": company.get("name", "Unknown"),
        })

    return result
