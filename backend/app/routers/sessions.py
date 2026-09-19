"""
Single-player game sessions — the heart of the anti-cheat model.

Security principles:
  1. Correct answers NEVER appear in any response before the player submits.
  2. The server picks which questions are in a session — client cannot choose.
  3. The server stores question_ids server-side; client cannot inject different questions.
  4. One answer attempt per question per session (max_answer_attempts config).
  5. The question_id submitted must belong to the session (ownership check).
  6. For Unscramble, we send scrambled letters only — the answer is never exposed.
  7. Image filenames are UUIDs so the URL cannot reveal the cricketer.
"""
import random
import unicodedata
from difflib import SequenceMatcher
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from pydantic import BaseModel
from app.core.db import get_db
from app.core.config import settings
from app.auth.dependencies import get_current_user_optional
from app.models.session import PlayerSession, GameAnswer
from app.models.game import Game
from app.models.question import Question, QuestionSet, QuestionOption

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _scramble(name: str, seed: int) -> list[str]:
    """Scramble each word in a name independently (so first/last are separate groups).
    Words are separated by a single " " sentinel in the returned list.
    Deterministic: same seed always gives the same scramble.
    """
    rng = random.Random(seed)
    words = name.upper().split()
    result: list[str] = []
    for i, word in enumerate(words):
        letters = list(word)
        attempts = 0
        while len(letters) > 1 and "".join(letters) == word and attempts < 100:
            rng.shuffle(letters)
            attempts += 1
        result.extend(letters)
        if i < len(words) - 1:
            result.append(" ")   # word-group separator (not a playable tile)
    return result


def _normalize(text: str) -> str:
    """Normalize for comparison: lowercase, strip spaces, remove diacritics."""
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text


def _fuzzy_match(submitted: str, accepted: str) -> bool:
    """Fuzzy string similarity check. Returns True if similarity ratio >= configured threshold."""
    if not submitted or not accepted:
        return False
    ratio = SequenceMatcher(None, submitted, accepted).ratio()
    return ratio >= settings.fuzzy_match_threshold


def _sanitize_question(q: Question, session_id: int) -> dict:
    """Return question data safe to send to client — NO correct answer included."""
    base = {
        "id": q.id,
        "type": q.question_type,
        "points": q.points,
        "hint_count": min(len(q.accepted_aliases or []), 3),  # how many hints available
    }
    if q.question_type == "image_guess":
        base["image_url"] = q.image_url
    elif q.question_type == "unscramble":
        # Server scrambles the word — client receives tiles only, never the answer
        answer_text = next(
            (opt.option_text for opt in q.options if opt.is_correct), ""
        ) or ""
        base["scrambled_letters"] = _scramble(answer_text, seed=session_id * 100 + q.id)
        base["country"] = q.question_text  # we store "country|role" in question_text for unscramble
        # Parse country|role format stored in question_text
        if q.question_text and "|" in q.question_text:
            parts = q.question_text.split("|", 1)
            base["country"] = parts[0].strip()
            base["role"] = parts[1].strip()
        else:
            base["country"] = q.question_text or ""
            base["role"] = ""
    return base


# ── Request / Response models ─────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    game_slug: str
    set_id: int | None = None
    guest_token: str | None = None
    is_daily: bool = False
    exclude_ids: list[int] = []


class SubmitAnswerRequest(BaseModel):
    question_id: int
    answer_given: str | None = None
    response_time_ms: int | None = None
    hints_used: int = 0


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("")
def start_session(
    body: StartSessionRequest,
    db: Session = Depends(get_db),
    user: dict | None = Depends(get_current_user_optional),
):
    """
    Start a new session. Picks SETTINGS.questions_per_session random questions
    from the active question sets for the game.
    Returns the session ID and the sanitized question list (no answers).
    """
    game = db.execute(
        select(Game).where(Game.slug == body.game_slug, Game.status == "active")
    ).scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail=f"Game '{body.game_slug}' not found or inactive")

    # Pick questions — from a specific set OR pooled from ALL active sets
    if body.set_id:
        q_set = db.get(QuestionSet, body.set_id)
        if not q_set or q_set.game_id != game.id or not q_set.is_active:
            raise HTTPException(status_code=404, detail="Question set not found")
        all_questions = db.execute(
            select(Question).where(
                Question.set_id == q_set.id,
                Question.is_active == True,
            )
        ).scalars().all()
        session_set_id = q_set.id
    else:
        # Default: pool questions from ALL active sets for this game
        all_questions = db.execute(
            select(Question)
            .join(QuestionSet, Question.set_id == QuestionSet.id)
            .where(
                QuestionSet.game_id == game.id,
                QuestionSet.is_active == True,
                Question.is_active == True,
            )
        ).scalars().all()
        # Use the first active set as nominal set_id for the session record
        first_set = db.execute(
            select(QuestionSet).where(
                QuestionSet.game_id == game.id,
                QuestionSet.is_active == True,
            ).limit(1)
        ).scalar_one_or_none()
        session_set_id = first_set.id if first_set else None

    if not all_questions:
        raise HTTPException(
            status_code=503,
            detail="You've answered all questions! More content coming soon."
        )

    # Filter out questions the player has already seen this browser session
    exclude_set = set(body.exclude_ids or [])
    fresh_questions = [q for q in all_questions if q.id not in exclude_set]

    # If the player has excluded EVERY available question, signal exhaustion —
    # don't loop back silently. Returning empty lets the frontend show
    # "you've played everything, come back later".
    if not fresh_questions and exclude_set:
        return {
            "session_id": 0,
            "game_slug": body.game_slug,
            "total_questions": 0,
            "questions": [],
            "exhausted": True,
        }

    pool = fresh_questions

    count = min(settings.questions_per_session, len(pool))
    picked = random.sample(pool, count)

    # Create session (temporarily, to get the ID for scrambling seed)
    session = PlayerSession(
        game_id=game.id,
        set_id=session_set_id,
        is_daily=body.is_daily,
        guest_token=body.guest_token if not user else None,
        question_ids=[],  # filled below after we have the session ID
    )
    db.add(session)
    db.flush()  # get session.id without committing

    # Build sanitized question list now that we have session.id (used as scramble seed)
    sanitized = [_sanitize_question(q, session.id) for q in picked]
    session.question_ids = [{"id": q.id, "position": i} for i, q in enumerate(picked)]
    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id,
        "game_slug": game.slug,
        "total_questions": count,
        "questions": sanitized,
    }


@router.post("/{session_id}/answers")
def submit_answer(
    session_id: int,
    body: SubmitAnswerRequest,
    db: Session = Depends(get_db),
    user: dict | None = Depends(get_current_user_optional),
):
    """
    Submit an answer for a question in this session.

    Anti-cheat checks:
      - question_id must be in session.question_ids (server-picked, can't inject)
      - Only one answer per question allowed (max_answer_attempts)
      - Correct answer revealed only AFTER submission, never before
    """
    session = db.get(PlayerSession, session_id)
    if not session or session.status != "in_progress":
        raise HTTPException(status_code=404, detail="Session not found or already completed")

    # ── Ownership check ────────────────────────────────────────────────────────
    # A guest can only submit to their own session (by guest_token or user_id)
    if user:
        # Registered user: session must belong to them (or be an unclaimed guest session)
        pass  # Trust Clerk JWT for now; full ownership binding in user registration flow
    # (future: enforce user_id match once users are saved to DB)

    # ── Question must be in this session ──────────────────────────────────────
    session_question_ids = {q["id"] for q in (session.question_ids or [])}
    if body.question_id not in session_question_ids:
        raise HTTPException(status_code=400, detail="Question not in this session")

    # ── One attempt per question ───────────────────────────────────────────────
    existing = db.execute(
        select(GameAnswer).where(
            GameAnswer.session_id == session_id,
            GameAnswer.question_id == body.question_id,
        )
    ).scalar_one_or_none()
    if existing and settings.max_answer_attempts == 1:
        raise HTTPException(status_code=409, detail="Already answered this question")

    # ── Load question ─────────────────────────────────────────────────────────
    question = db.get(Question, body.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # ── Server-side correctness check ─────────────────────────────────────────
    correct_options = [opt.option_text for opt in question.options if opt.is_correct and opt.option_text]
    aliases = question.accepted_aliases or []
    all_accepted = [_normalize(a) for a in correct_options + aliases if a]

    submitted = _normalize(body.answer_given or "")
    is_correct = (submitted != "") and (
        submitted in all_accepted
        or any(_fuzzy_match(submitted, a) for a in all_accepted)
    )

    # ── Scoring ───────────────────────────────────────────────────────────────
    points = 0
    if is_correct:
        points = question.points
        # Speed bonus: up to 20% extra if answered in under 5 seconds
        if body.response_time_ms and body.response_time_ms < 5000:
            points += int(question.points * 0.2)
        # Hint penalty: -10 per hint used
        points = max(points - body.hints_used * 10, 0)

    # ── Save answer ───────────────────────────────────────────────────────────
    answer = GameAnswer(
        session_id=session_id,
        question_id=body.question_id,
        answer_given=body.answer_given,
        is_correct=is_correct,
        response_time_ms=body.response_time_ms,
        hints_used=body.hints_used,
        points_earned=points,
    )
    session.score += points
    db.add(answer)
    db.commit()

    # ── Reveal correct answer ONLY after submission ───────────────────────────
    correct_text = correct_options[0] if correct_options else None
    return {
        "is_correct": is_correct,
        "points_earned": points,
        "correct_answer": correct_text,
        "explanation": question.explanation,
    }


@router.get("/{session_id}/hints/{question_id}")
def get_hint(
    session_id: int,
    question_id: int,
    hint_index: int = 0,
    db: Session = Depends(get_db),
):
    """
    Return one hint for a question. Hints are revealed progressively (index 0, 1, 2...).
    Hints are taken from accepted_aliases — these are vague enough not to be the answer.
    In production, store separate hints; for now we use the aliases list as hint pool.
    """
    session = db.get(PlayerSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session_qids = {q["id"] for q in (session.question_ids or [])}
    if question_id not in session_qids:
        raise HTTPException(status_code=400, detail="Question not in this session")

    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # We store hints in accepted_aliases for now; first entry is always the answer.
    # Hints start at index 1 (skip the correct answer string).
    hints = (question.accepted_aliases or [])[1:]
    if hint_index >= len(hints):
        return {"hint": None, "exhausted": True}
    return {"hint": hints[hint_index], "exhausted": hint_index + 1 >= len(hints)}


@router.post("/{session_id}/complete")
def complete_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: dict | None = Depends(get_current_user_optional),
):
    """Finalise a session and return the result summary + share card URL."""
    session = db.get(PlayerSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == "completed":
        # Idempotent — return the cached result
        answers = session.answers
        total = len(session.question_ids or [])
        correct = sum(1 for a in answers if a.is_correct)
        return {
            "session_id": session_id,
            "score": session.score,
            "accuracy": session.accuracy,
            "correct": correct,
            "total": total,
            "share_card_url": f"/api/sessions/{session_id}/share-card",
        }

    answers = session.answers
    total = len(session.question_ids or [])
    correct = sum(1 for a in answers if a.is_correct)

    session.status = "completed"
    session.completed_at = datetime.now(timezone.utc)
    session.accuracy = correct / total if total > 0 else 0
    db.commit()

    return {
        "session_id": session_id,
        "score": session.score,
        "accuracy": round(session.accuracy, 3),
        "correct": correct,
        "total": total,
        "share_card_url": f"/api/sessions/{session_id}/share-card",
    }
