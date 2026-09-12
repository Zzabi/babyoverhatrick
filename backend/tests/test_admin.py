"""
Tests for the /api/admin/* endpoints.

All endpoints require HTTP Basic Auth. Tests cover:
  - Authentication (401 without credentials, 200 with valid credentials)
  - Game and set management
  - Question CRUD (add, list, delete, patch)
  - Cricketer CRUD
  - Image upload (mocked storage)
"""
import base64
from unittest.mock import patch


def bad_headers():
    creds = base64.b64encode(b"wrong:credentials").decode()
    return {"Authorization": f"Basic {creds}"}


# ── Authentication ────────────────────────────────────────────────────────────

class TestAdminAuth:
    def test_list_games_requires_auth(self, client):
        resp = client.get("/api/admin/games")
        assert resp.status_code == 401

    def test_list_games_wrong_credentials(self, client):
        resp = client.get("/api/admin/games", headers=bad_headers())
        assert resp.status_code == 401

    def test_list_games_valid_credentials(self, client, admin_headers, guess_game):
        resp = client.get("/api/admin/games", headers=admin_headers)
        assert resp.status_code == 200


# ── Admin games ───────────────────────────────────────────────────────────────

class TestAdminGames:
    def test_list_games(self, client, admin_headers, guess_game, unscramble_game):
        resp = client.get("/api/admin/games", headers=admin_headers)
        assert resp.status_code == 200
        slugs = [g["slug"] for g in resp.json()]
        assert "guess-the-cricketer" in slugs
        assert "unscramble-the-name" in slugs

    def test_list_games_empty(self, client, admin_headers):
        resp = client.get("/api/admin/games", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []


# ── Question sets ─────────────────────────────────────────────────────────────

class TestAdminSets:
    def test_list_sets(self, client, admin_headers, guess_game):
        resp = client.get("/api/admin/games/guess-the-cricketer/sets", headers=admin_headers)
        assert resp.status_code == 200
        sets = resp.json()
        assert len(sets) >= 1
        assert sets[0]["name"] == "Default Set"

    def test_list_sets_not_found(self, client, admin_headers):
        resp = client.get("/api/admin/games/no-such-game/sets", headers=admin_headers)
        assert resp.status_code == 404

    def test_create_set(self, client, admin_headers, guess_game):
        resp = client.post(
            "/api/admin/games/guess-the-cricketer/sets",
            json={"name": "IPL Legends", "difficulty": "hard", "is_active": True},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "IPL Legends"
        assert "id" in data

    def test_create_set_game_not_found(self, client, admin_headers):
        resp = client.post(
            "/api/admin/games/no-such/sets",
            json={"name": "Test Set"},
            headers=admin_headers,
        )
        assert resp.status_code == 404


# ── Questions ─────────────────────────────────────────────────────────────────

class TestAdminQuestions:
    def test_list_questions(self, client, admin_headers, guess_game):
        resp = client.get(
            f"/api/admin/games/guess-the-cricketer/questions?set_id={guess_game['set'].id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        questions = resp.json()
        assert len(questions) == 12  # seeded 12 questions

    def test_list_questions_includes_correct_answer(self, client, admin_headers, guess_game):
        """Admin list reveals the correct answer — this is intentional for content management."""
        resp = client.get(
            f"/api/admin/games/guess-the-cricketer/questions?set_id={guess_game['set'].id}",
            headers=admin_headers,
        )
        questions = resp.json()
        assert questions[0]["correct_answer"] is not None

    def test_list_questions_game_not_found(self, client, admin_headers):
        resp = client.get("/api/admin/games/no-such/questions", headers=admin_headers)
        assert resp.status_code == 404

    def test_delete_question(self, client, admin_headers, guess_game, db):
        from app.models.question import Question
        q_id = guess_game["questions"][0].id

        resp = client.delete(f"/api/admin/questions/{q_id}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

        # Expire the session cache so we see the committed delete
        db.expire_all()
        deleted = db.get(Question, q_id)
        assert deleted is None

    def test_delete_question_not_found(self, client, admin_headers):
        resp = client.delete("/api/admin/questions/999999", headers=admin_headers)
        assert resp.status_code == 404

    def test_patch_question_answer(self, client, admin_headers, guess_game, db):
        """PATCH /api/admin/questions/{id} can update the answer."""
        q_id = guess_game["questions"][0].id
        resp = client.patch(
            f"/api/admin/questions/{q_id}",
            json={"answer": "Updated Name"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["correct_answer"] == "Updated Name"

    def test_patch_question_difficulty(self, client, admin_headers, guess_game):
        q_id = guess_game["questions"][0].id
        resp = client.patch(
            f"/api/admin/questions/{q_id}",
            json={"difficulty": "hard"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["difficulty"] == "hard"

    def test_patch_question_deactivate(self, client, admin_headers, guess_game):
        q_id = guess_game["questions"][0].id
        resp = client.patch(
            f"/api/admin/questions/{q_id}",
            json={"is_active": False},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_patch_question_aliases(self, client, admin_headers, guess_game):
        q_id = guess_game["questions"][0].id
        resp = client.patch(
            f"/api/admin/questions/{q_id}",
            json={"aliases": ["Alias One", "Alias Two"]},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert "Alias One" in resp.json()["aliases"]

    def test_patch_question_not_found(self, client, admin_headers):
        resp = client.patch(
            "/api/admin/questions/999999",
            json={"difficulty": "easy"},
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_patch_unscramble_country_role(self, client, admin_headers, unscramble_game):
        """PATCH updates country and role stored in question_text for unscramble questions."""
        q_id = unscramble_game["questions"][0].id
        resp = client.patch(
            f"/api/admin/questions/{q_id}",
            json={"country": "AUS", "role": "Bowler"},
            headers=admin_headers,
        )
        assert resp.status_code == 200

    def test_add_image_guess_question(self, client, admin_headers, guess_game):
        """POST /api/admin/questions/image-guess adds a question (URL provided, no upload)."""
        resp = client.post(
            "/api/admin/questions/image-guess",
            data={
                "game_slug": "guess-the-cricketer",
                "set_id": str(guess_game["set"].id),
                "image_url": "http://localhost:9000/test-bucket/questions/abc123.jpg",
                "answer": "Rohit Sharma",
                "aliases": "RoHit, Hitman",
                "difficulty": "medium",
                "points": "100",
                "explanation": "Indian batting legend",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "question_id" in data
        assert data["image_url"] == "http://localhost:9000/test-bucket/questions/abc123.jpg"

    def test_add_image_guess_question_auto_adds_cricketer(self, client, admin_headers, guess_game, db):
        """Adding an image-guess question auto-adds the cricketer to autocomplete list."""
        from app.models.cricketer import Cricketer
        from sqlalchemy import select

        client.post(
            "/api/admin/questions/image-guess",
            data={
                "game_slug": "guess-the-cricketer",
                "set_id": str(guess_game["set"].id),
                "image_url": "http://localhost:9000/test-bucket/questions/new.jpg",
                "answer": "MS Dhoni",
            },
            headers=admin_headers,
        )

        cricketer = db.execute(select(Cricketer).where(Cricketer.name == "MS Dhoni")).scalar_one_or_none()
        assert cricketer is not None

    def test_add_image_guess_question_invalid_set(self, client, admin_headers):
        resp = client.post(
            "/api/admin/questions/image-guess",
            data={"game_slug": "guess-the-cricketer", "set_id": "999999", "image_url": "http://x/a.jpg", "answer": "X"},
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_add_unscramble_question(self, client, admin_headers, unscramble_game):
        resp = client.post(
            "/api/admin/questions/unscramble",
            json={
                "game_slug": "unscramble-the-name",
                "set_id": unscramble_game["set"].id,
                "answer": "ROHIT SHARMA",
                "country": "IND",
                "role": "Opening batter",
                "difficulty": "easy",
                "points": 100,
                "hints": ["Hitman", "Mumbai Indians captain"],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert "question_id" in resp.json()

    def test_add_unscramble_question_invalid_set(self, client, admin_headers):
        resp = client.post(
            "/api/admin/questions/unscramble",
            json={"game_slug": "unscramble-the-name", "set_id": 999999, "answer": "KOHLI", "country": "IND", "role": "Batter"},
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_upload_image(self, client, admin_headers):
        """POST /api/admin/upload-image mocked — returns a URL."""
        with patch("app.routers.admin_content.upload_bytes", return_value="http://localhost:9000/test-bucket/questions/mocked.jpg"):
            resp = client.post(
                "/api/admin/upload-image",
                files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")},
                headers=admin_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "url" in data
        assert "key" in data

    def test_upload_image_invalid_type(self, client, admin_headers):
        """Non-image content type is rejected."""
        resp = client.post(
            "/api/admin/upload-image",
            files={"file": ("test.pdf", b"fake-pdf-bytes", "application/pdf")},
            headers=admin_headers,
        )
        assert resp.status_code == 400


# ── Cricketers ────────────────────────────────────────────────────────────────

class TestAdminCricketers:
    def test_list_cricketers_empty(self, client, admin_headers):
        resp = client.get("/api/admin/cricketers", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_cricketers(self, client, admin_headers, seeded_cricketer):
        resp = client.get("/api/admin/cricketers", headers=admin_headers)
        assert resp.status_code == 200
        names = [c["name"] for c in resp.json()]
        assert "Virat Kohli" in names

    def test_add_cricketer(self, client, admin_headers):
        resp = client.post(
            "/api/admin/cricketers",
            json={"name": "Rohit Sharma", "country": "IND"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Rohit Sharma"

    def test_add_cricketer_duplicate(self, client, admin_headers, seeded_cricketer):
        """Adding an existing cricketer returns the existing record with already_exists=True."""
        resp = client.post(
            "/api/admin/cricketers",
            json={"name": "Virat Kohli", "country": "IND"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json().get("already_exists") is True

    def test_delete_cricketer(self, client, admin_headers, seeded_cricketer, db):
        from app.models.cricketer import Cricketer
        # Capture ID before expire_all() so accessing .id doesn't trigger a reload
        cricketer_id = seeded_cricketer.id
        resp = client.delete(f"/api/admin/cricketers/{cricketer_id}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True
        db.expire_all()
        assert db.get(Cricketer, cricketer_id) is None

    def test_delete_cricketer_not_found(self, client, admin_headers):
        resp = client.delete("/api/admin/cricketers/999999", headers=admin_headers)
        assert resp.status_code == 404

    def test_patch_cricketer_name(self, client, admin_headers, seeded_cricketer):
        resp = client.patch(
            f"/api/admin/cricketers/{seeded_cricketer.id}",
            json={"name": "King Kohli"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "King Kohli"

    def test_patch_cricketer_country(self, client, admin_headers, seeded_cricketer):
        resp = client.patch(
            f"/api/admin/cricketers/{seeded_cricketer.id}",
            json={"country": "eng"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["country"] == "ENG"  # stored uppercase

    def test_patch_cricketer_not_found(self, client, admin_headers):
        resp = client.patch(
            "/api/admin/cricketers/999999",
            json={"name": "Nobody"},
            headers=admin_headers,
        )
        assert resp.status_code == 404
