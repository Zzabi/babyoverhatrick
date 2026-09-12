from sqlalchemy import Integer, Date, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
from app.models.base import Base


class Streak(Base):
    """
    Tracks a registered user's consecutive daily play streak per game.
    Guests track streaks in localStorage — this table is for registered users only.
    On registration, the backend scans player_sessions by guest_token and
    reconstructs the streak from historical sessions ('claim your streak' path).
    """
    __tablename__ = "streaks"
    __table_args__ = (
        UniqueConstraint("user_id", "game_id", name="uq_streak_user_game"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), index=True)

    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_played_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships
    user: Mapped["User"] = relationship(back_populates="streaks")  # noqa: F821
    game: Mapped["Game"] = relationship(back_populates="streaks")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Streak user={self.user_id} game={self.game_id} current={self.current_streak}>"
