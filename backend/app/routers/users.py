from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from pydantic import BaseModel
from app.core.db import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.session import PlayerSession

router = APIRouter()


@router.get("/me")
def get_profile(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Return the current user's profile, streaks, and recent session history."""
    db_user = db.execute(
        select(User).where(User.clerk_user_id == user["sub"])
    ).scalar_one_or_none()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found — complete registration first")

    return {
        "id": db_user.id,
        "username": db_user.username,
        "email": db_user.email,
        "avatar_url": db_user.avatar_url,
        "role": db_user.role,
    }


class ClaimGuestRequest(BaseModel):
    guest_token: str


@router.post("/claim-guest")
def claim_guest_sessions(
    body: ClaimGuestRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Transfer all sessions played as a guest to the now-registered user.
    Called on signup — the 'claim your streak' path from the PRD.
    """
    db_user = db.execute(
        select(User).where(User.clerk_user_id == user["sub"])
    ).scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    result = db.execute(
        update(PlayerSession)
        .where(
            PlayerSession.guest_token == body.guest_token,
            PlayerSession.user_id.is_(None),
        )
        .values(user_id=db_user.id, guest_token=None)
    )
    db.commit()
    return {"sessions_claimed": result.rowcount}
