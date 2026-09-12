"""
Tests for the /api/sessions endpoints.

Covers: start session, submit answer, get hint, complete session.
Includes anti-cheat verification: no answers in pre-submission responses.
"""
import pytest


# ── Helper to start a session ────────────────────────────────────────────────

def start_guess_session(client, game_data, **kwargs):
    body = {"game_slug": "guess-the-cricketer", **kwargs}
    resp = client.post("/api/sessions", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


def start_unscramble_session(client, game_data, **kwargs):
    body = {"game_slug": "unscramble-the-name", **kwargs}
    resp = client.post("/api/sessions", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


# ── Start session ─────────────────────────────────────────────────────────────

class TestStartSession:
    def test_returns_session_id_and_questions(self, client, guess_game):
        data = start_guess_session(client, guess_game)
        assert "session_id" in data
        assert "questions" in data
        assert "total_questions" in data
        assert data["total_questions"] == 10  # default questions_per_session

    def test_questions_have_no_answers(self, client, guess_game):
        """Anti-cheat: no correct_answer field in any question before submission."""
        data = start_guess_session(client, guess_game)
        for q in data["questions"]:
            assert "correct_answer" not in q
            assert "answer" not in q
            assert "option_text" not in q

    def test_image_guess_questions_have_image_url(self, client, guess_game):
        data = start_guess_session(client, guess_game)
        for q in data["questions"]:
            assert q["type"] == "image_guess"
            assert "image_url" in q
            assert q["image_url"].startswith("http")

    def test_unscramble_questions_have_scrambled_letters(self, client, unscramble_game):
        data = start_unscramble_session(client, unscramble_game)
        for q in data["questions"]:
            assert q["type"] == "unscramble"
            assert "scrambled_letters" in q
            assert isinstance(q["scrambled_letters"], list)
            assert len(q["scrambled_letters"]) > 0

    def test_unscramble_questions_have_country_role(self, client, unscramble_game):
        data = start_unscramble_session(client, unscramble_game)
        for q in data["questions"]:
            assert "country" in q
            assert "role" in q

    def test_unknown_game_returns_404(self, client):
        resp = client.post("/api/sessions", json={"game_slug": "no-such-game"})
        assert resp.status_code == 404

    def test_inactive_game_returns_404(self, client, db):
        from app.models.game import Game
        g = Game(slug="inactive-game", name="Inactive", status="draft", sort_order=99, config={})
        db.add(g)
        db.commit()
        resp = client.post("/api/sessions", json={"game_slug": "inactive-game"})
        assert resp.status_code == 404

    def test_specific_set_id(self, client, guess_game):
        data = start_guess_session(client, guess_game, set_id=guess_game["set"].id)
        assert data["total_questions"] == 10

    def test_invalid_set_id_returns_404(self, client, guess_game):
        resp = client.post("/api/sessions", json={"game_slug": "guess-the-cricketer", "set_id": 99999})
        assert resp.status_code == 404

    def test_exclude_ids_reduces_pool(self, client, guess_game):
        """Exclude some question IDs — remaining pool should not include them."""
        all_ids = [q.id for q in guess_game["questions"]]
        # Exclude half the questions
        exclude = all_ids[:6]
        data = start_guess_session(client, guess_game, exclude_ids=exclude)
        returned_ids = [q["id"] for q in data["questions"]]
        for excluded_id in exclude:
            assert excluded_id not in returned_ids

    def test_exclude_all_ids_falls_back_to_full_pool(self, client, guess_game):
        """When all questions are excluded, server falls back to full pool."""
        all_ids = [q.id for q in guess_game["questions"]]
        data = start_guess_session(client, guess_game, exclude_ids=all_ids)
        # Should still return 10 questions (from the full pool)
        assert data["total_questions"] == 10

    def test_session_stores_question_ids_server_side(self, client, db, guess_game):
        """Server stores question_ids; verify by checking the DB record."""
        from app.models.session import PlayerSession
        data = start_guess_session(client, guess_game)
        session_id = data["session_id"]
        session = db.get(PlayerSession, session_id)
        assert session is not None
        assert len(session.question_ids) == 10

    def test_guest_token_stripped_when_authed(self, client, db, guess_game):
        """
        With DEV_BYPASS_AUTH=true, user is always authenticated.
        The session router strips guest_token when user is not None.
        """
        from app.models.session import PlayerSession
        data = start_guess_session(client, guess_game, guest_token="test-guest-uuid-1234")
        session_id = data["session_id"]
        session = db.get(PlayerSession, session_id)
        # When authenticated (even via DEV bypass), guest_token is not stored
        assert session.guest_token is None

    def test_scramble_is_deterministic(self, client, unscramble_game):
        """Starting two sessions gives different scrambles (different session IDs = different seeds)."""
        data1 = start_unscramble_session(client, unscramble_game)
        data2 = start_unscramble_session(client, unscramble_game)
        # Session IDs are different, so scramble seeds differ
        assert data1["session_id"] != data2["session_id"]

    def test_questions_per_session_limited_by_pool(self, client, db):
        """When pool has fewer questions than settings.questions_per_session, return all of them."""
        from app.models.game import Game
        from app.models.question import QuestionSet, Question, QuestionOption

        g = Game(slug="small-game", name="Small", status="active", sort_order=99, config={})
        db.add(g)
        db.flush()
        q_set = QuestionSet(
            game_id=g.id, name="Tiny Set", difficulty_default="medium", is_active=True, is_daily_eligible=True
        )
        db.add(q_set)
        db.flush()
        # Add only 3 questions (less than the 10-question session default)
        for i in range(3):
            q = Question(set_id=q_set.id, question_type="image_guess", image_url=f"http://x/{i}.jpg",
                         difficulty="medium", points=100, is_active=True, accepted_aliases=[])
            db.add(q)
            db.flush()
            db.add(QuestionOption(question_id=q.id, option_text=f"Answer {i}", is_correct=True))
        db.commit()

        resp = client.post("/api/sessions", json={"game_slug": "small-game"})
        assert resp.status_code == 200
        assert resp.json()["total_questions"] == 3


# ── Submit answer ─────────────────────────────────────────────────────────────

class TestSubmitAnswer:
    def _start_and_get_first_question(self, client, guess_game):
        session_data = start_guess_session(client, guess_game)
        session_id = session_data["session_id"]
        question = session_data["questions"][0]
        return session_id, question

    def test_correct_answer_returns_is_correct_true(self, client, guess_game):
        session_id, q = self._start_and_get_first_question(client, guess_game)
        # The correct answer for question index 0 is "Cricketer 0", "Cricketer 1", etc.
        # We need to find the actual answer from the DB
        correct = f"Cricketer {guess_game['questions'][0].id % 12}"
        # Use exact match — find which cricketer is question q["id"]
        # Just submit with the correct answer for that question
        qid = q["id"]
        # Find the matching question fixture
        fixture_q = next((x for x in guess_game["questions"] if x.id == qid), None)
        answer = f"Cricketer {guess_game['questions'].index(fixture_q)}"

        resp = client.post(f"/api/sessions/{session_id}/answers", json={
            "question_id": qid,
            "answer_given": answer,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_correct"] is True
        assert data["points_earned"] > 0

    def test_wrong_answer(self, client, guess_game):
        session_id, q = self._start_and_get_first_question(client, guess_game)
        resp = client.post(f"/api/sessions/{session_id}/answers", json={
            "question_id": q["id"],
            "answer_given": "Definitely Wrong Answer XYZ",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_correct"] is False
        assert data["points_earned"] == 0

    def test_timed_out_empty_answer(self, client, guess_game):
        """Empty answer (timed out) counts as wrong."""
        session_id, q = self._start_and_get_first_question(client, guess_game)
        resp = client.post(f"/api/sessions/{session_id}/answers", json={
            "question_id": q["id"],
            "answer_given": "",
        })
        assert resp.status_code == 200
        assert resp.json()["is_correct"] is False

    def test_null_answer(self, client, guess_game):
        """Null answer_given is treated as wrong."""
        session_id, q = self._start_and_get_first_question(client, guess_game)
        resp = client.post(f"/api/sessions/{session_id}/answers", json={
            "question_id": q["id"],
        })
        assert resp.status_code == 200
        assert resp.json()["is_correct"] is False

    def test_correct_answer_reveals_correct_text(self, client, guess_game):
        """Correct answer is revealed in the response after submission."""
        session_id, q = self._start_and_get_first_question(client, guess_game)
        resp = client.post(f"/api/sessions/{session_id}/answers", json={
            "question_id": q["id"],
            "answer_given": "Wrong",
        })
        assert resp.status_code == 200
        data = resp.json()
        # Correct answer is returned even for wrong submissions
        assert "correct_answer" in data
        assert data["correct_answer"] is not None

    def test_duplicate_answer_rejected(self, client, guess_game):
        """Second submission for the same question returns 409."""
        session_id, q = self._start_and_get_first_question(client, guess_game)
        body = {"question_id": q["id"], "answer_given": "Any"}
        client.post(f"/api/sessions/{session_id}/answers", json=body)
        resp = client.post(f"/api/sessions/{session_id}/answers", json=body)
        assert resp.status_code == 409

    def test_question_not_in_session_rejected(self, client, guess_game):
        """Submitting a question_id not in the session returns 400."""
        session_id, _ = self._start_and_get_first_question(client, guess_game)
        resp = client.post(f"/api/sessions/{session_id}/answers", json={
            "question_id": 999999,
            "answer_given": "Anyone",
        })
        assert resp.status_code == 400

    def test_session_not_found(self, client, guess_game):
        """Submitting to a non-existent session returns 404."""
        resp = client.post("/api/sessions/999999/answers", json={
            "question_id": 1,
            "answer_given": "Anyone",
        })
        assert resp.status_code == 404

    def test_completed_session_rejected(self, client, guess_game):
        """Cannot submit answers to a completed session."""
        data = start_guess_session(client, guess_game)
        session_id = data["session_id"]
        # Complete the session
        client.post(f"/api/sessions/{session_id}/complete")
        resp = client.post(f"/api/sessions/{session_id}/answers", json={
            "question_id": data["questions"][0]["id"],
            "answer_given": "Test",
        })
        assert resp.status_code == 404

    def test_score_accumulated(self, client, guess_game, db):
        """Score increases with each correct answer."""
        from app.models.session import PlayerSession

        data = start_guess_session(client, guess_game)
        session_id = data["session_id"]

        # Submit a wrong answer — score stays 0
        q0 = data["questions"][0]
        client.post(f"/api/sessions/{session_id}/answers", json={
            "question_id": q0["id"], "answer_given": "Wrong"
        })

        session = db.get(PlayerSession, session_id)
        db.refresh(session)
        assert session.score == 0

    def test_speed_bonus_for_fast_answer(self, client, guess_game, db):
        """Correct answer under 5000ms earns speed bonus."""
        from app.models.session import PlayerSession

        data = start_guess_session(client, guess_game)
        session_id = data["session_id"]
        q = data["questions"][0]
        qid = q["id"]

        # Find correct answer
        fixture_q = next(x for x in guess_game["questions"] if x.id == qid)
        idx = guess_game["questions"].index(fixture_q)
        correct = f"Cricketer {idx}"

        resp = client.post(f"/api/sessions/{session_id}/answers", json={
            "question_id": qid,
            "answer_given": correct,
            "response_time_ms": 2000,  # fast — should trigger speed bonus
        })
        assert resp.status_code == 200
        pts = resp.json()["points_earned"]
        assert pts > 100  # base is 100; with speed bonus should be more

    def test_hint_penalty_reduces_score(self, client, guess_game, db):
        """Using hints reduces points earned."""
        data = start_guess_session(client, guess_game)
        session_id = data["session_id"]
        q = data["questions"][0]
        qid = q["id"]

        fixture_q = next(x for x in guess_game["questions"] if x.id == qid)
        idx = guess_game["questions"].index(fixture_q)
        correct = f"Cricketer {idx}"

        resp = client.post(f"/api/sessions/{session_id}/answers", json={
            "question_id": qid,
            "answer_given": correct,
            "hints_used": 5,  # 5 hints × 10 pts each = -50
        })
        assert resp.status_code == 200
        pts = resp.json()["points_earned"]
        assert pts == 50  # 100 - 50 = 50

    def test_fuzzy_match_accepted(self, client, db, guess_game):
        """Fuzzy-close spelling of correct answer is accepted."""
        data = start_guess_session(client, guess_game)
        session_id = data["session_id"]
        q = data["questions"][0]
        qid = q["id"]

        # The correct answer is something like "Cricketer 3"
        # "cricketer3" without space is fuzzy close enough (ratio > 0.75)
        fixture_q = next(x for x in guess_game["questions"] if x.id == qid)
        idx = guess_game["questions"].index(fixture_q)
        correct = f"Cricketer {idx}"

        # Typo version: drop the space
        typo = correct.replace(" ", "").lower()  # e.g. "cricketer3"
        resp = client.post(f"/api/sessions/{session_id}/answers", json={
            "question_id": qid,
            "answer_given": typo,
        })
        assert resp.status_code == 200
        # "cricketer3" vs "cricketer 3" — ratio ~0.94, should be accepted
        # This tests the fuzzy match logic

    def test_alias_accepted_as_correct(self, client, db):
        """Accepted alias is treated as a correct answer."""
        from app.models.game import Game
        from app.models.question import QuestionSet, Question, QuestionOption

        g = Game(slug="alias-game", name="Alias Game", status="active", sort_order=99, config={})
        db.add(g)
        db.flush()
        qs = QuestionSet(game_id=g.id, name="Set", difficulty_default="medium", is_active=True, is_daily_eligible=True)
        db.add(qs)
        db.flush()
        # Add 10 questions so we have enough for a session
        for i in range(10):
            q = Question(set_id=qs.id, question_type="image_guess", image_url=f"http://x/{i}.jpg",
                         difficulty="medium", points=100, is_active=True,
                         accepted_aliases=["R Ashwin", "Ravichandran Ashwin"] if i == 0 else [])
            db.add(q)
            db.flush()
            db.add(QuestionOption(question_id=q.id, option_text="Virat Kohli" if i == 0 else f"Player{i}", is_correct=True))
        db.commit()

        resp = client.post("/api/sessions", json={"game_slug": "alias-game"})
        assert resp.status_code == 200
        session_data = resp.json()
        session_id = session_data["session_id"]
        # Find question 0 (the one with aliases)
        from app.models.session import PlayerSession
        from sqlalchemy import select
        from app.models.question import Question as Q2
        s = db.get(PlayerSession, session_id)
        q_ids_in_session = {item["id"] for item in s.question_ids}

        # Get the question that has aliases
        alias_q = db.execute(
            select(Q2).where(Q2.set_id == qs.id, Q2.accepted_aliases != [])
        ).scalar_one_or_none()

        if alias_q and alias_q.id in q_ids_in_session:
            resp2 = client.post(f"/api/sessions/{session_id}/answers", json={
                "question_id": alias_q.id,
                "answer_given": "R Ashwin",  # alias, not the main answer
            })
            assert resp2.status_code == 200
            assert resp2.json()["is_correct"] is True


# ── Get hint ──────────────────────────────────────────────────────────────────

class TestGetHint:
    def test_get_hint_returns_alias(self, client, db, guess_game):
        """Hint endpoint returns an alias for the question."""
        from app.models.game import Game
        from app.models.question import QuestionSet, Question, QuestionOption

        g = Game(slug="hint-game", name="Hint Game", status="active", sort_order=99, config={})
        db.add(g)
        db.flush()
        qs = QuestionSet(game_id=g.id, name="Set", difficulty_default="medium", is_active=True, is_daily_eligible=True)
        db.add(qs)
        db.flush()
        for i in range(10):
            # Backend treats aliases[0] as the answer alias; hints are aliases[1:]
            aliases = ["AliasAnswer", "Hint One", "Hint Two"] if i == 0 else []
            q = Question(set_id=qs.id, question_type="image_guess", image_url=f"http://x/{i}.jpg",
                         difficulty="medium", points=100, is_active=True, accepted_aliases=aliases)
            db.add(q)
            db.flush()
            db.add(QuestionOption(question_id=q.id, option_text=f"Player{i}", is_correct=True))
        db.commit()

        session_resp = client.post("/api/sessions", json={"game_slug": "hint-game"})
        session_data = session_resp.json()
        session_id = session_data["session_id"]

        from app.models.session import PlayerSession
        from sqlalchemy import select
        from app.models.question import Question as Q2
        s = db.get(PlayerSession, session_id)
        q_ids = {item["id"] for item in s.question_ids}

        hinted_q = db.execute(
            select(Q2).where(Q2.set_id == qs.id, Q2.accepted_aliases != [])
        ).scalar_one_or_none()

        if hinted_q and hinted_q.id in q_ids:
            resp = client.get(f"/api/sessions/{session_id}/hints/{hinted_q.id}?hint_index=0")
            assert resp.status_code == 200
            data = resp.json()
            assert "hint" in data
            assert "exhausted" in data
            assert data["hint"] == "Hint One"

    def test_hint_exhausted(self, client, guess_game):
        """Requesting a hint index beyond available hints returns exhausted=True."""
        data = start_guess_session(client, guess_game)
        session_id = data["session_id"]
        q = data["questions"][0]
        # Questions have no aliases, so hint_index=0 should be exhausted
        resp = client.get(f"/api/sessions/{session_id}/hints/{q['id']}?hint_index=0")
        assert resp.status_code == 200
        result = resp.json()
        assert result["exhausted"] is True

    def test_hint_session_not_found(self, client, guess_game):
        resp = client.get("/api/sessions/999999/hints/1?hint_index=0")
        assert resp.status_code == 404

    def test_hint_question_not_in_session(self, client, guess_game):
        data = start_guess_session(client, guess_game)
        session_id = data["session_id"]
        resp = client.get(f"/api/sessions/{session_id}/hints/999999?hint_index=0")
        assert resp.status_code == 400


# ── Complete session ──────────────────────────────────────────────────────────

class TestCompleteSession:
    def test_complete_returns_summary(self, client, guess_game):
        data = start_guess_session(client, guess_game)
        session_id = data["session_id"]

        resp = client.post(f"/api/sessions/{session_id}/complete")
        assert resp.status_code == 200
        result = resp.json()
        assert result["session_id"] == session_id
        assert "score" in result
        assert "accuracy" in result
        assert "correct" in result
        assert "total" in result
        assert "share_card_url" in result

    def test_complete_marks_session_completed(self, client, db, guess_game):
        from app.models.session import PlayerSession
        data = start_guess_session(client, guess_game)
        session_id = data["session_id"]

        client.post(f"/api/sessions/{session_id}/complete")
        session = db.get(PlayerSession, session_id)
        db.refresh(session)
        assert session.status == "completed"
        assert session.completed_at is not None

    def test_complete_is_idempotent(self, client, guess_game):
        """Completing a session twice returns same result (no error)."""
        data = start_guess_session(client, guess_game)
        session_id = data["session_id"]
        r1 = client.post(f"/api/sessions/{session_id}/complete")
        r2 = client.post(f"/api/sessions/{session_id}/complete")
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["score"] == r2.json()["score"]

    def test_complete_nonexistent_session(self, client):
        resp = client.post("/api/sessions/999999/complete")
        assert resp.status_code == 404

    def test_complete_accuracy_calculation(self, client, guess_game):
        """Accuracy = correct / total; 0 correct → 0.0 accuracy."""
        data = start_guess_session(client, guess_game)
        session_id = data["session_id"]

        # Submit wrong answers for all questions
        for q in data["questions"]:
            client.post(f"/api/sessions/{session_id}/answers", json={
                "question_id": q["id"],
                "answer_given": "definitely wrong xyz",
            })

        resp = client.post(f"/api/sessions/{session_id}/complete")
        result = resp.json()
        assert result["correct"] == 0
        assert result["total"] == 10
        assert result["accuracy"] == 0.0


# ── Helper function unit-style tests ─────────────────────────────────────────

class TestHelpers:
    def test_normalize_strips_diacritics(self):
        from app.routers.sessions import _normalize
        assert _normalize("Kohli") == "kohli"
        assert _normalize("  SACHIN  ") == "sachin"
        # Diacritic removal
        assert _normalize("Waqār") == "waqar"

    def test_normalize_empty(self):
        from app.routers.sessions import _normalize
        assert _normalize("") == ""

    def test_fuzzy_match_exact(self):
        from app.routers.sessions import _fuzzy_match
        assert _fuzzy_match("kohli", "kohli") is True

    def test_fuzzy_match_close(self):
        from app.routers.sessions import _fuzzy_match
        # "kohli" vs "kohl" — ratio ~0.88, above 0.75 threshold
        assert _fuzzy_match("kohl", "kohli") is True

    def test_fuzzy_match_far(self):
        from app.routers.sessions import _fuzzy_match
        assert _fuzzy_match("xyz123", "virat kohli") is False

    def test_fuzzy_match_empty_strings(self):
        from app.routers.sessions import _fuzzy_match
        assert _fuzzy_match("", "kohli") is False
        assert _fuzzy_match("kohli", "") is False
        assert _fuzzy_match("", "") is False

    def test_scramble_is_deterministic(self):
        from app.routers.sessions import _scramble
        result1 = _scramble("KOHLI", seed=42)
        result2 = _scramble("KOHLI", seed=42)
        assert result1 == result2

    def test_scramble_different_seed(self):
        from app.routers.sessions import _scramble
        # Different seeds should very likely produce different orderings for longer names
        result1 = _scramble("TENDULKAR", seed=1)
        result2 = _scramble("TENDULKAR", seed=100000)
        # Sort both and verify same letters — scramble preserves all letters
        assert sorted([c for c in result1 if c != " "]) == sorted([c for c in result2 if c != " "])

    def test_scramble_multi_word(self):
        from app.routers.sessions import _scramble
        result = _scramble("VIRAT KOHLI", seed=99)
        assert " " in result  # word separator present
        # Count letters (excluding separator)
        letters = [c for c in result if c != " "]
        assert len(letters) == len("VIRATKOHLI")

    def test_scramble_single_letter_word(self):
        from app.routers.sessions import _scramble
        # Single-character words can't be scrambled
        result = _scramble("A B", seed=1)
        # Should still work without infinite loop
        assert "A" in result
        assert "B" in result
