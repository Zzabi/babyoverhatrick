from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.models.base import Base


class PlayerSession(Base):
    """
    A single-player game session (Phase 1).
    user_id is nullable — guests play without an account.
    guest_token (UUID stored in browser localStorage) links guest sessions to a user on signup.

    question_ids stores the ordered list of question IDs picked for this session, along with
    any server-computed display data (scrambled letters for unscramble questions).
    Correct answers are NEVER stored here — they live in the questions/options tables.
    """
    __tablename__ = "player_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    guest_token: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)  # UUID v4
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), index=True)
    set_id: Mapped[int | None] = mapped_column(ForeignKey("question_sets.id"), nullable=True)
    is_daily: Mapped[bool] = mapped_column(default=False)

    # Ordered list of question dicts for this session.
    # Each dict: {id, type, image_url, scrambled_letters (unscramble only), country, role}
    # Correct answers deliberately omitted.
    question_ids: Mapped[list] = mapped_column(JSONB, default=list)

    score: Mapped[int] = mapped_column(Integer, default=0)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_taken_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="in_progress")  # in_progress | completed | abandoned

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # relationships
    user: Mapped["User | None"] = relationship(back_populates="sessions")  # noqa: F821
    game: Mapped["Game"] = relationship(back_populates="sessions")  # noqa: F821
    answers: Mapped[list["GameAnswer"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    share_events: Mapped[list["ShareEvent"]] = relationship(back_populates="session")  # noqa: F821

    def __repr__(self) -> str:
        return f"<PlayerSession id={self.id} status={self.status} score={self.score}>"


class GameAnswer(Base):
    """
    Each individual answer submitted within a session.
    The server validates correctness — the client never knows the answer in advance.
    """
    __tablename__ = "game_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("player_sessions.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)  # for rate-limiting duplicate submissions

    answer_given: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool] = mapped_column(default=False)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hints_used: Mapped[int] = mapped_column(Integer, default=0)
    points_earned: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # relationships
    session: Mapped["PlayerSession"] = relationship(back_populates="answers")
    question: Mapped["Question"] = relationship(back_populates="game_answers")  # noqa: F821

    def __repr__(self) -> str:
        return f"<GameAnswer id={self.id} correct={self.is_correct} pts={self.points_earned}>"
