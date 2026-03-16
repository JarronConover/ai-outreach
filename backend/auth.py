"""
Supabase JWT verification for FastAPI.

Verifies tokens by calling Supabase's /auth/v1/user endpoint.
This works with Supabase's new asymmetric JWT signing keys — no secret needed.
Results are cached for 5 minutes to avoid per-request latency.

Every request (except /health) must carry:
    Authorization: Bearer <supabase_access_token>
"""
import asyncio
import os
import time

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_UNPROTECTED = {"/health"}
_CACHE_TTL = 300  # seconds

# token -> (valid_until_timestamp, is_valid)
_cache: dict[str, tuple[float, bool]] = {}


async def _verify_token(token: str) -> bool:
    now = time.time()
    if token in _cache:
        valid_until, is_valid = _cache[token]
        if now < valid_until:
            return is_valid

    try:
        from backend.db.client import get_db
        sb = get_db()
        result = await asyncio.to_thread(sb.auth.get_user, token)
        is_valid = result.user is not None
    except Exception:
        is_valid = False

    _cache[token] = (now + _CACHE_TTL, is_valid)
    return is_valid


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _UNPROTECTED:
            return await call_next(request)

        if not os.getenv("SUPABASE_URL"):
            # Not configured — skip auth (local dev fallback)
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse({"detail": "Not authenticated"}, status_code=401)

        token = auth_header.removeprefix("Bearer ").strip()
        if not await _verify_token(token):
            return JSONResponse({"detail": "Invalid or expired token"}, status_code=401)

        return await call_next(request)
