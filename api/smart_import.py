"""Backward-compatibility shim — real implementation is in backend/services/smart_import.py."""
from backend.services.smart_import import smart_import_csv  # noqa: F401

__all__ = ["smart_import_csv"]
