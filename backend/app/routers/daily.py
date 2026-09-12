from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import date
from app.core.db import get_db
from app.models.game import Game
from app.models.daily import DailyChallenge

router = APIRouter()


@router.get("")
def get_todays_challenges(db: Session = Depends(get_db)):
    """
    Returns all scheduled daily challenges for today across all active games.
    Used by the homepage to highlight the Daily Challenge section.
    """
    today = date.today()
    rows = db.execute(
        select(DailyChallenge, Game)
        .join(Game, DailyChallenge.game_id == Game.id)
        .where(
            DailyChallenge.challenge_date == today,
            Game.status == "active",
        )
    ).all()

    return [
        {
            "game_slug": game.slug,
            "game_name": game.name,
            "set_id": challenge.set_id,
            "date": str(today),
        }
        for challenge, game in rows
    ]
