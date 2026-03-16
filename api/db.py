"""Backward-compatibility shim — real implementation is in backend/db/client.py."""
from backend.db.client import get_db  # noqa: F401

__all__ = ["get_db"]
