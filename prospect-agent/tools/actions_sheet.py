"""Supabase-backed CRUD for the Actions table.

Replaces the gspread implementation. Delegates to api.supabase_crud which
owns the canonical Supabase actions functions used by all agents.
"""
from __future__ import annotations

import os
import sys
from typing import Optional

# Ensure project root is in sys.path so `api.*` resolves correctly.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from api.supabase_crud import (  # noqa: E402
    get_actions as _get_actions,
    get_action_by_id as _get_action_by_id,
    write_actions as _write_actions,
    update_action_status as _update_action_status,
    batch_update_action_status as _batch_update_action_status,
    cancel_pending_actions as _cancel_pending_actions,
    delete_pending_actions as _delete_pending_actions,
)


def get_actions(status_filter=None):
    """Return actions from Supabase, optionally filtered by status."""
    return _get_actions(status=status_filter)


def get_action_by_id(action_id):
    """Return a single action dict by ID, or None if not found."""
    return _get_action_by_id(action_id)


def write_actions(actions):
    """Insert new pending actions into Supabase."""
    _write_actions(actions)


def update_action_status(action_id, status, confirmed_at=None):
    """Update the status of a single action."""
    _update_action_status(action_id, status, confirmed_at)


def batch_update_action_status(action_ids, status, confirmed_at=None):
    """Update status for multiple actions in one Supabase call."""
    _batch_update_action_status(action_ids, status, confirmed_at)


def cancel_pending_actions():
    """Mark all actions with status='pending' as 'canceled'."""
    _cancel_pending_actions()


def clear_all_actions():
    """Delete all pending and confirming actions (used before writing a fresh plan)."""
    _delete_pending_actions()
