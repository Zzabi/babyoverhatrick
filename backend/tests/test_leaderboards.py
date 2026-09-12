"""Tests for GET /api/leaderboards/{slug} endpoint."""
from datetime import datetime, timezone


def _complete_session(client, game_slug, score_override=None, guest_token=None):
    """Helper: start a session, skip answers, complete it, return session_id."""
    body = {"game_slug": game_slug}
    if guest_token:
        body["guest_token"] = guest_token
    start = client.post("/api/sessions", json=body)
    assert start.status_code == 200, start.text
    session_id = start.json()["session_id"]
    client.post(f"/api/sessions/{session_id}/complete")
    return session_id


def _set_score(db, session_id, score):
    """Directly set a session score for leaderboard testing."""
    from app.models.session import PlayerSession
    s = db.get(PlayerSession, session_id)
    s.score = score
    db.commit()


class TestLeaderboard:
    def test_unknown_game_returns_empty_entries(self, client):
        """Unknown game slug returns empty entries (not 404)."""
        resp = client.get("/api/leaderboards/no-such-game")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entries"] == []

    def test_empty_leaderboard(self, client, guess_game):
        """No completed sessions → empty entries."""
        resp = client.get("/api/leaderboards/guess-the-cricketer")
        assert resp.status_code == 200
        assert resp.json()["entries"] == []

    def test_guest_sessions_appear(self, client, guess_game, db):
        """Completed guest sessions appear in the leaderboard."""
        sid = _complete_session(client, "guess-the-cricketer", guest_token="guest-abc")
        _set_score(db, sid, 500)

        resp = client.get("/api/leaderboards/guess-the-cricketer")
        assert resp.status_code == 200
        entries = resp.json()["entries"]
        assert len(entries) == 1
        assert entries[0]["username"] == "Guest"
        assert entries[0]["score"] == 500

    def test_zero_score_guests_excluded(self, client, guess_game, db):
        """Guest sessions with score=0 are excluded from leaderboard."""
        sid = _complete_session(client, "guess-the-cricketer", guest_token="guest-zero")
        _set_score(db, sid, 0)

        resp = client.get("/api/leaderboards/guess-the-cricketer")
        assert resp.json()["entries"] == []

    def test_scores_sorted_descending(self, client, guess_game, db):
        """Leaderboard entries are sorted by score descending."""
        sid1 = _complete_session(client, "guess-the-cricketer", guest_token="g1")
        sid2 = _complete_session(client, "guess-the-cricketer", guest_token="g2")
        sid3 = _complete_session(client, "guess-the-cricketer", guest_token="g3")
        _set_score(db, sid1, 300)
        _set_score(db, sid2, 800)
        _set_score(db, sid3, 500)

        resp = client.get("/api/leaderboards/guess-the-cricketer")
        scores = [e["score"] for e in resp.json()["entries"]]
        assert scores == sorted(scores, reverse=True)

    def test_period_daily(self, client, guess_game, db):
        """period=daily filters to today's sessions only."""
        sid = _complete_session(client, "guess-the-cricketer", guest_token="daily-g")
        _set_score(db, sid, 400)

        resp = client.get("/api/leaderboards/guess-the-cricketer?period=daily")
        assert resp.status_code == 200
        entries = resp.json()["entries"]
        assert len(entries) == 1

    def test_period_all_time(self, client, guess_game, db):
        """period=all_time returns all completed sessions."""
        sid = _complete_session(client, "guess-the-cricketer", guest_token="alltime-g")
        _set_score(db, sid, 600)

        resp = client.get("/api/leaderboards/guess-the-cricketer?period=all_time")
        assert resp.status_code == 200
        assert len(resp.json()["entries"]) >= 1

    def test_rank_field_present(self, client, guess_game, db):
        """Each entry has a rank field starting at 1."""
        sid = _complete_session(client, "guess-the-cricketer", guest_token="rank-g")
        _set_score(db, sid, 700)

        resp = client.get("/api/leaderboards/guess-the-cricketer")
        entries = resp.json()["entries"]
        assert entries[0]["rank"] == 1

    def test_response_structure(self, client, guess_game):
        """Response always has game, period, and entries keys."""
        resp = client.get("/api/leaderboards/guess-the-cricketer")
        data = resp.json()
        assert "game" in data
        assert "period" in data
        assert "entries" in data
        assert data["game"] == "guess-the-cricketer"
