"""Backward-compatibility shim — real implementation is in backend/db/crud.py."""
from backend.db.crud import (  # noqa: F401
    get_people,
    get_people_by_email,
    get_companies,
    get_company_map,
    get_demos,
    get_stats,
    get_actions,
    get_pending_actions,
    get_action_by_id,
    write_actions,
    update_action_status,
    batch_update_action_status,
    cancel_pending_actions,
    delete_pending_actions,
    get_emails,
    get_emails_needing_response,
    update_email_status,
)

__all__ = [
    "get_people", "get_people_by_email",
    "get_companies", "get_company_map",
    "get_demos", "get_stats",
    "get_actions", "get_pending_actions", "get_action_by_id",
    "write_actions", "update_action_status", "batch_update_action_status",
    "cancel_pending_actions", "delete_pending_actions",
    "get_emails", "get_emails_needing_response", "update_email_status",
]
