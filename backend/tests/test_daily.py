"""Tests for GET /api/daily endpoint."""
from datetime import date


class TestDailyEndpoint:
    def test_daily_empty_when_no_challenges_scheduled(self, client):
        """Returns empty list when no daily challenges are set up."""
        resp = client.get("/api/daily")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_daily_returns_todays_challenges(self, client, db, guess_game):
        """Returns today's scheduled challenges."""
        from app.models.daily import DailyChallenge
        today = date.today()
        challenge = DailyChallenge(
            game_id=guess_game["game"].id,
            set_id=guess_game["set"].id,
            challenge_date=today,
        )
        db.add(challenge)
        db.commit()

        resp = client.get("/api/daily")
        assert resp.status_code == 200
        challenges = resp.json()
        assert len(challenges) == 1
        assert challenges[0]["set_id"] == guess_game["set"].id

    def test_daily_does_not_return_future_challenges(self, client, db, guess_game):
        """Challenges for future dates are not returned."""
        from app.models.daily import DailyChallenge
        from datetime import timedelta
        tomorrow = date.today() + timedelta(days=1)
        challenge = DailyChallenge(
            game_id=guess_game["game"].id,
            set_id=guess_game["set"].id,
            challenge_date=tomorrow,
        )
        db.add(challenge)
        db.commit()

        resp = client.get("/api/daily")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_daily_response_structure(self, client, db, guess_game):
        """Each challenge entry has the expected fields."""
        from app.models.daily import DailyChallenge
        today = date.today()
        challenge = DailyChallenge(
            game_id=guess_game["game"].id,
            set_id=guess_game["set"].id,
            challenge_date=today,
        )
        db.add(challenge)
        db.commit()

        resp = client.get("/api/daily")
        entry = resp.json()[0]
        assert "game_slug" in entry
        assert "game_name" in entry
        assert "set_id" in entry
        assert "date" in entry
