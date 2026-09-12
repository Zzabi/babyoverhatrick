from sqlalchemy import Integer, Float, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.models.base import Base


class LeaderboardEntry(Base):
    """
    Aggregated best-score record per (user, game).
    Updated when a player session completes.
    Daily leaderboards are computed from player_sessions filtered by completed_at date.
    """
    __tablename__ = "leaderboard_entries"
    __table_args__ = (
        UniqueConstraint("user_id", "game_id", name="uq_leaderboard_user_game"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    best_score: Mapped[int] = mapped_column(Integer, default=0)
    best_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    games_played: Mapped[int] = mapped_column(Integer, default=0)
    total_score: Mapped[int] = mapped_column(Integer, default=0)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)  # cached rank, recomputed periodically

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships
    game: Mapped["Game"] = relationship(back_populates="leaderboard_entries")  # noqa: F821
    user: Mapped["User"] = relationship(back_populates="leaderboard_entries")  # noqa: F821

    def __repr__(self) -> str:
        return f"<LeaderboardEntry user={self.user_id} game={self.game_id} best={self.best_score}>"
