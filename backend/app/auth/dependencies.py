"""
Auth dependencies for FastAPI route injection.

DEV_BYPASS_AUTH=true  →  every request is automatically authenticated as a dev admin.
                          Never enable in production.

Production flow:
  1. Client sends  Authorization: Bearer <clerk_jwt>
  2. get_current_user() fetches JWKS from Clerk, validates JWT, returns user dict
  3. get_current_user_optional() returns None for unauthenticated requests (guest routes)
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from httpx import AsyncClient
from app.core.config import settings
import json

security = HTTPBearer(auto_error=False)

# Cached JWKS — refreshed lazily
_jwks_cache: dict | None = None


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None and settings.clerk_jwks_url:
        async with AsyncClient() as client:
            resp = await client.get(settings.clerk_jwks_url)
            _jwks_cache = resp.json()
    return _jwks_cache or {}


def _dev_user() -> dict:
    """Returns a fake admin user for local development."""
    return {
        "sub": settings.dev_user_id,
        "email": settings.dev_user_email,
        "role": settings.dev_user_role,
        "is_dev": True,
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """
    Requires authentication. Use on protected routes.
    In dev-bypass mode, returns a fake admin user with no token needed.
    """
    if settings.dev_bypass_auth:
        return _dev_user()

    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        jwks = await _get_jwks()
        payload = jwt.decode(
            credentials.credentials,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}")


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict | None:
    """
    Optional authentication. Use on guest-playable routes.
    Returns the user dict if authenticated, None if guest.
    In dev-bypass mode, still returns the dev user.
    """
    if settings.dev_bypass_auth:
        return _dev_user()

    if not credentials:
        return None

    try:
        jwks = await _get_jwks()
        payload = jwt.decode(
            credentials.credentials,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload
    except JWTError:
        return None


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Requires the 'admin' role. Use on CMS/admin routes."""
    role = user.get("role") or user.get("publicMetadata", {}).get("role", "user")
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
