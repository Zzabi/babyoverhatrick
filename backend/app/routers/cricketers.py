from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.db import get_db
from app.models.cricketer import Cricketer

router = APIRouter()


@router.get("/search")
def search_cricketers(
    q: str = Query("", min_length=1, max_length=100),
    limit: int = Query(10, le=20),
    db: Session = Depends(get_db),
):
    """
    Autocomplete search for cricketer names.
    Used by the Guess the Cricketer game's text input.
    Returns name list only — no correct-answer context included.
    """
    if len(q) < 1:
        return []

    results = db.execute(
        select(Cricketer.id, Cricketer.name, Cricketer.country)
        .where(Cricketer.name.ilike(f"%{q}%"))
        .order_by(Cricketer.name)
        .limit(limit)
    ).all()

    return [{"id": r.id, "name": r.name, "country": r.country} for r in results]
