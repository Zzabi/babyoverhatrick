from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from datetime import date, datetime, timezone
from app.core.db import get_db
from app.models.game import Game
from app.models.session import PlayerSession
from app.models.user import User

router = APIRouter()


@router.get("/{slug}")
def get_leaderboard(
    slug: str,
    period: str = Query("all_time", pattern="^(daily|all_time)$"),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db),
):
    """
    Returns top scores for a game.
    Includes both registered users AND guest sessions.
    period=daily → today's scores only.
    period=all_time → best score ever per user/guest.
    """
    game = db.execute(select(Game).where(Game.slug == slug)).scalar_one_or_none()
    if not game:
        return {"game": slug, "period": period, "entries": []}

    # ── Registered-user leaderboard ────────────────────────────────────────────
    # Group by user_id; use their stored username
    user_query = (
        select(
            User.username.label("name"),
            func.max(PlayerSession.score).label("best_score"),
            func.count(PlayerSession.id).label("plays"),
        )
        .join(User, PlayerSession.user_id == User.id)
        .where(
            PlayerSession.game_id == game.id,
            PlayerSession.status == "completed",
            PlayerSession.user_id.is_not(None),
        )
        .group_by(User.id, User.username)
        .order_by(desc("best_score"))
    )

    # ── Guest leaderboard ──────────────────────────────────────────────────────
    # Each guest session is its own row — guests have no persistent identity.
    guest_query = (
        select(PlayerSession.score)
        .where(
            PlayerSession.game_id == game.id,
            PlayerSession.status == "completed",
            PlayerSession.user_id.is_(None),
            PlayerSession.score > 0,
        )
        .order_by(desc(PlayerSession.score))
    )

    if period == "daily":
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        user_query = user_query.where(PlayerSession.completed_at >= today_start)
        guest_query = guest_query.where(PlayerSession.completed_at >= today_start)

    user_rows = db.execute(user_query).all()
    guest_scores = db.execute(guest_query.limit(limit)).scalars().all()

    # Merge and sort by score descending, take top `limit`
    combined = [
        {"name": r.name, "score": r.best_score, "plays": r.plays}
        for r in user_rows
    ] + [
        {"name": "Guest", "score": s, "plays": 1}
        for s in guest_scores
    ]
    combined.sort(key=lambda x: x["score"], reverse=True)
    combined = combined[:limit]

    return {
        "game": slug,
        "period": period,
        "entries": [
            {
                "rank": i + 1,
                "username": row["name"],
                "score": row["score"],
                "plays": row["plays"],
            }
            for i, row in enumerate(combined)
        ],
    }
