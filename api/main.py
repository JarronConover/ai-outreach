"""
Backward-compatibility shim.

The real FastAPI app now lives in backend/main.py.
Both entry points work:
    uvicorn backend.main:app --reload   ← preferred
    uvicorn api.main:app --reload       ← legacy alias
"""
from backend.main import app  # noqa: F401

__all__ = ["app"]
