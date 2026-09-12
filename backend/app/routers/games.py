from datetime import date, datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.core.db import get_db
from app.models.game import Game
from app.models.question import QuestionSet
from app.models.daily import DailyChallenge
from app.models.session import PlayerSession

router = APIRouter()


@router.get("")
def list_games(db: Session = Depends(get_db)):
    """List all active games for the homepage game hub."""
    games = db.execute(
        select(Game).where(Game.status == "active").order_by(Game.sort_order)
    ).scalars().all()

    result = []
    for g in games:
        stats = _game_stats(g.id, db)
        result.append({
            "id": g.id,
            "slug": g.slug,
            "name": g.name,
            "description": g.description,
            "cover_image_url": g.cover_image_url,
            "config": g.config,
            "players_today": stats["players_today"],
        })
    return result


@router.get("/{slug}")
def get_game(slug: str, db: Session = Depends(get_db)):
    """Get a game's detail and config."""
    game = db.execute(select(Game).where(Game.slug == slug)).scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return {
        "id": game.id,
        "slug": game.slug,
        "name": game.name,
        "description": game.description,
        "cover_image_url": game.cover_image_url,
        "config": game.config,
        "status": game.status,
    }


@router.get("/{slug}/sets")
def list_game_sets(slug: str, db: Session = Depends(get_db)):
    """Public: return active question sets for a game (for set-picker UI)."""
    game = db.execute(select(Game).where(Game.slug == slug)).scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    sets = db.execute(
        select(QuestionSet).where(
            QuestionSet.game_id == game.id,
            QuestionSet.is_active == True,
        ).order_by(QuestionSet.id)
    ).scalars().all()
    return [{"id": s.id, "name": s.name, "difficulty": s.difficulty_default} for s in sets]


@router.get("/{slug}/stats")
def get_game_stats(slug: str, db: Session = Depends(get_db)):
    """Return real player counts for this game."""
    game = db.execute(select(Game).where(Game.slug == slug)).scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return _game_stats(game.id, db)


@router.get("/{slug}/daily")
def get_daily_challenge(slug: str, db: Session = Depends(get_db)):
    """
    Return today's daily challenge set for a game (midnight IST refresh).
    If no challenge is scheduled, deterministically pick a set based on date
    so all players worldwide get the same questions on the same day.
    """
    game = db.execute(select(Game).where(Game.slug == slug)).scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    today = date.today()

    # Scheduled challenge wins
    challenge = db.execute(
        select(DailyChallenge).where(
            DailyChallenge.game_id == game.id,
            DailyChallenge.challenge_date == today,
        )
    ).scalar_one_or_none()
    if challenge:
        return {"set_id": challenge.set_id, "is_scheduled": True, "date": str(today)}

    # Deterministic fallback: same set for everyone on the same day
    active_sets = db.execute(
        select(QuestionSet).where(
            QuestionSet.game_id == game.id,
            QuestionSet.is_active == True,
            QuestionSet.is_daily_eligible == True,
        )
    ).scalars().all()

    if not active_sets:
        raise HTTPException(status_code=404, detail="No content available for today")

    # Use ordinal day number to cycle through sets — predictable, not random
    idx = today.toordinal() % len(active_sets)
    chosen = active_sets[idx]
    return {"set_id": chosen.id, "is_scheduled": False, "date": str(today)}


# ── Internal helper ───────────────────────────────────────────────────────────

def _game_stats(game_id: int, db: Session) -> dict:
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    players_today = db.execute(
        select(func.count(PlayerSession.id)).where(
            PlayerSession.game_id == game_id,
            PlayerSession.status == "completed",
            PlayerSession.completed_at >= today,
        )
    ).scalar() or 0
    players_total = db.execute(
        select(func.count(PlayerSession.id)).where(
            PlayerSession.game_id == game_id,
            PlayerSession.status == "completed",
        )
    ).scalar() or 0
    return {"players_today": players_today, "players_total": players_total}
