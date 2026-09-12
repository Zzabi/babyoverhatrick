"""
Tests for app/auth/dependencies.py.

With DEV_BYPASS_AUTH=true (set in conftest), the bypass path is already
covered by every other test file.  Here we test the production code paths by
patching settings.dev_bypass_auth=False and mocking the JWKS / JWT decode calls.
"""
from unittest.mock import patch, AsyncMock
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.auth.dependencies import (
    get_current_user,
    get_current_user_optional,
    require_admin,
)


# ---------------------------------------------------------------------------
# Helpers — lightweight FastAPI apps without DEV_BYPASS_AUTH
# ---------------------------------------------------------------------------

def _make_auth_app():
    """A tiny FastAPI app that exposes auth-protected routes for testing."""
    app = FastAPI()

    @app.get("/protected")
    async def protected(user: dict = Depends(get_current_user)):
        return {"sub": user.get("sub")}

    @app.get("/optional")
    async def optional(user: dict | None = Depends(get_current_user_optional)):
        return {"authenticated": user is not None}

    @app.get("/admin-only")
    async def admin_only(user: dict = Depends(require_admin)):
        return {"role": user.get("role")}

    return app


# ---------------------------------------------------------------------------
# get_current_user — no credentials → 401
# ---------------------------------------------------------------------------

def test_get_current_user_no_credentials_returns_401():
    """Without a Bearer token, protected routes return 401."""
    app = _make_auth_app()

    with patch("app.auth.dependencies.settings") as mock_settings:
        mock_settings.dev_bypass_auth = False
        mock_settings.clerk_jwks_url = "https://example.com/jwks"

        with TestClient(app, raise_server_exceptions=True) as c:
            resp = c.get("/protected")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# get_current_user — valid JWT → 200
# ---------------------------------------------------------------------------

def test_get_current_user_valid_jwt_returns_200():
    """A valid JWT is decoded and the user dict is returned."""
    app = _make_auth_app()

    fake_payload = {"sub": "user_abc123", "email": "test@example.com"}

    with patch("app.auth.dependencies.settings") as mock_settings:
        mock_settings.dev_bypass_auth = False
        mock_settings.clerk_jwks_url = "https://example.com/jwks"

        with patch("app.auth.dependencies._get_jwks", new_callable=AsyncMock, return_value={"keys": []}):
            with patch("app.auth.dependencies.jwt.decode", return_value=fake_payload):
                with TestClient(app) as c:
                    resp = c.get("/protected", headers={"Authorization": "Bearer faketoken"})
        assert resp.status_code == 200
        assert resp.json()["sub"] == "user_abc123"


# ---------------------------------------------------------------------------
# get_current_user — invalid JWT → 401
# ---------------------------------------------------------------------------

def test_get_current_user_invalid_jwt_returns_401():
    """An invalid JWT raises JWTError which is surfaced as 401."""
    from jose import JWTError
    app = _make_auth_app()

    with patch("app.auth.dependencies.settings") as mock_settings:
        mock_settings.dev_bypass_auth = False
        mock_settings.clerk_jwks_url = "https://example.com/jwks"

        with patch("app.auth.dependencies._get_jwks", new_callable=AsyncMock, return_value={"keys": []}):
            with patch("app.auth.dependencies.jwt.decode", side_effect=JWTError("bad token")):
                with TestClient(app) as c:
                    resp = c.get("/protected", headers={"Authorization": "Bearer badtoken"})
        assert resp.status_code == 401
        assert "Invalid token" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# get_current_user_optional — no credentials → guest (None) → 200
# ---------------------------------------------------------------------------

def test_get_current_user_optional_no_credentials_returns_guest():
    """Optional auth route is reachable without a token — user is None (guest)."""
    app = _make_auth_app()

    with patch("app.auth.dependencies.settings") as mock_settings:
        mock_settings.dev_bypass_auth = False
        mock_settings.clerk_jwks_url = "https://example.com/jwks"

        with TestClient(app) as c:
            resp = c.get("/optional")
        assert resp.status_code == 200
        assert resp.json()["authenticated"] is False


# ---------------------------------------------------------------------------
# get_current_user_optional — invalid JWT → silently returns None
# ---------------------------------------------------------------------------

def test_get_current_user_optional_invalid_jwt_returns_none():
    """Optional auth silently returns None for an invalid token (guest fallback)."""
    from jose import JWTError
    app = _make_auth_app()

    with patch("app.auth.dependencies.settings") as mock_settings:
        mock_settings.dev_bypass_auth = False
        mock_settings.clerk_jwks_url = "https://example.com/jwks"

        with patch("app.auth.dependencies._get_jwks", new_callable=AsyncMock, return_value={"keys": []}):
            with patch("app.auth.dependencies.jwt.decode", side_effect=JWTError("bad")):
                with TestClient(app) as c:
                    resp = c.get("/optional", headers={"Authorization": "Bearer badtoken"})
        assert resp.status_code == 200
        assert resp.json()["authenticated"] is False


# ---------------------------------------------------------------------------
# require_admin — non-admin role → 403
# ---------------------------------------------------------------------------

def test_require_admin_non_admin_role_returns_403():
    """A user without the admin role is rejected with 403."""
    app = _make_auth_app()

    fake_payload = {"sub": "user_xyz", "role": "user"}

    with patch("app.auth.dependencies.settings") as mock_settings:
        mock_settings.dev_bypass_auth = False
        mock_settings.clerk_jwks_url = "https://example.com/jwks"

        with patch("app.auth.dependencies._get_jwks", new_callable=AsyncMock, return_value={"keys": []}):
            with patch("app.auth.dependencies.jwt.decode", return_value=fake_payload):
                with TestClient(app) as c:
                    resp = c.get("/admin-only", headers={"Authorization": "Bearer sometoken"})
        assert resp.status_code == 403
        assert "Admin access required" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# require_admin — admin role via publicMetadata → 200
# ---------------------------------------------------------------------------

def test_require_admin_via_public_metadata():
    """Clerk JWTs may embed role in publicMetadata; require_admin handles both."""
    app = _make_auth_app()

    fake_payload = {"sub": "user_meta", "publicMetadata": {"role": "admin"}}

    with patch("app.auth.dependencies.settings") as mock_settings:
        mock_settings.dev_bypass_auth = False
        mock_settings.clerk_jwks_url = "https://example.com/jwks"

        with patch("app.auth.dependencies._get_jwks", new_callable=AsyncMock, return_value={"keys": []}):
            with patch("app.auth.dependencies.jwt.decode", return_value=fake_payload):
                with TestClient(app) as c:
                    resp = c.get("/admin-only", headers={"Authorization": "Bearer sometoken"})
        assert resp.status_code == 200
