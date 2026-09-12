"""Tests for the /api/games endpoints."""
from datetime import datetime, timezone


def test_list_games_empty(client):
    """Returns empty list when no games exist."""
    resp = client.get("/api/games")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_games_active_only(client, db):
    """Only active games appear in the list; draft/archived are excluded."""
    from app.models.game import Game
    db.add(Game(slug="active-game", name="Active", status="active", sort_order=1, config={}))
    db.add(Game(slug="draft-game", name="Draft", status="draft", sort_order=2, config={}))
    db.add(Game(slug="archived-game", name="Archived", status="archived", sort_order=3, config={}))
    db.commit()

    resp = client.get("/api/games")
    assert resp.status_code == 200
    slugs = [g["slug"] for g in resp.json()]
    assert "active-game" in slugs
    assert "draft-game" not in slugs
    assert "archived-game" not in slugs


def test_list_games_includes_players_today(client, guess_game):
    """games list includes players_today count."""
    resp = client.get("/api/games")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert "players_today" in data[0]
    assert data[0]["players_today"] == 0  # no completed sessions yet


def test_list_games_sorted_by_sort_order(client, db):
    """Games returned in sort_order ascending order."""
    from app.models.game import Game
    db.add(Game(slug="game-b", name="B", status="active", sort_order=2, config={}))
    db.add(Game(slug="game-a", name="A", status="active", sort_order=1, config={}))
    db.commit()

    resp = client.get("/api/games")
    slugs = [g["slug"] for g in resp.json()]
    assert slugs.index("game-a") < slugs.index("game-b")


def test_get_game_found(client, guess_game):
    """GET /api/games/{slug} returns game detail."""
    resp = client.get("/api/games/guess-the-cricketer")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "guess-the-cricketer"
    assert data["name"] == "Guess the Cricketer"
    assert "status" in data


def test_get_game_not_found(client):
    """GET /api/games/{slug} returns 404 for unknown slug."""
    resp = client.get("/api/games/nonexistent-game")
    assert resp.status_code == 404


def test_list_game_sets(client, guess_game):
    """GET /api/games/{slug}/sets returns active sets."""
    resp = client.get("/api/games/guess-the-cricketer/sets")
    assert resp.status_code == 200
    sets = resp.json()
    assert len(sets) == 1
    assert sets[0]["name"] == "Default Set"
    assert "id" in sets[0]
    assert "difficulty" in sets[0]


def test_list_game_sets_not_found(client):
    """Returns 404 for unknown game slug."""
    resp = client.get("/api/games/unknown-game/sets")
    assert resp.status_code == 404


def test_get_game_stats(client, guess_game):
    """GET /api/games/{slug}/stats returns player counts."""
    resp = client.get("/api/games/guess-the-cricketer/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "players_today" in data
    assert "players_total" in data
    assert data["players_today"] == 0
    assert data["players_total"] == 0


def test_get_game_stats_not_found(client):
    """Returns 404 for unknown game."""
    resp = client.get("/api/games/no-such-game/stats")
    assert resp.status_code == 404


def test_get_daily_challenge_deterministic(client, guess_game):
    """Daily challenge falls back to deterministic set selection when none is scheduled."""
    resp = client.get("/api/games/guess-the-cricketer/daily")
    assert resp.status_code == 200
    data = resp.json()
    assert "set_id" in data
    assert data["is_scheduled"] is False
    assert "date" in data


def test_get_daily_challenge_no_sets(client, db):
    """Returns 404 if no eligible sets exist for daily challenge."""
    from app.models.game import Game
    from app.models.question import QuestionSet
    g = Game(slug="empty-game", name="Empty", status="active", sort_order=1, config={})
    db.add(g)
    db.flush()
    # No question sets added
    db.commit()

    resp = client.get("/api/games/empty-game/daily")
    assert resp.status_code == 404


def test_get_daily_challenge_scheduled(client, guess_game, db):
    """Scheduled daily challenge takes priority over deterministic fallback."""
    from datetime import date
    from app.models.daily import DailyChallenge

    today = date.today()
    challenge = DailyChallenge(
        game_id=guess_game["game"].id,
        set_id=guess_game["set"].id,
        challenge_date=today,
    )
    db.add(challenge)
    db.commit()

    resp = client.get("/api/games/guess-the-cricketer/daily")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_scheduled"] is True
    assert data["set_id"] == guess_game["set"].id


def test_get_daily_challenge_game_not_found(client):
    """Returns 404 for unknown game slug."""
    resp = client.get("/api/games/no-such/daily")
    assert resp.status_code == 404
