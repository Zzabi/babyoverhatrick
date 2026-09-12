"""
Tests for /api/users/* endpoints.

With DEV_BYPASS_AUTH=true, get_current_user() returns a mock dev user dict
with sub=settings.dev_user_id. Routes that do a DB lookup for this user_id
will return 404 unless we seed the user first.
"""
from app.core.config import settings


class TestUsersMe:
    def test_get_me_without_db_user_returns_404(self, client):
        """
        With DEV_BYPASS_AUTH, auth passes but the DB lookup finds no matching user.
        This is the expected behaviour when a user has authenticated via Clerk
        but hasn't been registered in the local DB yet.
        """
        resp = client.get("/api/users/me")
        assert resp.status_code == 404

    def test_get_me_with_registered_user(self, client, db):
        """If a User row exists with the matching clerk_user_id, profile is returned."""
        from app.models.user import User
        user = User(
            clerk_user_id=settings.dev_user_id,
            username="devuser",
            email="dev@local.test",
            role="admin",
        )
        db.add(user)
        db.commit()

        resp = client.get("/api/users/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "devuser"
        assert data["email"] == "dev@local.test"

    def test_get_me_response_fields(self, client, db):
        """Response contains the expected fields."""
        from app.models.user import User
        db.add(User(
            clerk_user_id=settings.dev_user_id,
            username="tester",
            email="tester@local.test",
        ))
        db.commit()

        resp = client.get("/api/users/me")
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "username" in data
        assert "email" in data


class TestClaimGuestSessions:
    def test_claim_requires_registered_user(self, client):
        """claim-guest returns 404 when user is not in the DB."""
        resp = client.post("/api/users/claim-guest", json={"guest_token": "any-token"})
        assert resp.status_code == 404

    def test_claim_missing_token_is_422(self, client):
        """Pydantic validation: missing guest_token returns 422."""
        resp = client.post("/api/users/claim-guest", json={})
        assert resp.status_code == 422

    def test_claim_success(self, client, db, guess_game):
        """When user exists, claim-guest transfers sessions."""
        from app.models.user import User
        from app.models.session import PlayerSession

        # Register the dev user
        user = User(
            clerk_user_id=settings.dev_user_id,
            username="testclaimer",
            email="claimer@test.com",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create a guest session manually (bypass the API which strips guest_token when authed)
        session = PlayerSession(
            game_id=guess_game["game"].id,
            guest_token="claim-test-xyz",
            question_ids=[],
            status="completed",
        )
        db.add(session)
        db.commit()

        resp = client.post("/api/users/claim-guest", json={"guest_token": "claim-test-xyz"})
        assert resp.status_code == 200
        result = resp.json()
        assert "sessions_claimed" in result
        assert result["sessions_claimed"] >= 1
