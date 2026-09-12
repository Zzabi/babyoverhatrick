from sqlalchemy import Date, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
from app.models.base import Base


class DailyChallenge(Base):
    """
    One curated deck per game per day, same for every player globally.
    Refreshed at midnight IST. Content team schedules these in advance via Admin CMS.
    The backend reads today's row and caches the set_id in Redis until midnight.
    """
    __tablename__ = "daily_challenges"
    __table_args__ = (
        UniqueConstraint("game_id", "challenge_date", name="uq_daily_game_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), index=True)
    set_id: Mapped[int] = mapped_column(ForeignKey("question_sets.id"))
    challenge_date: Mapped[date] = mapped_column(Date, index=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # relationships
    game: Mapped["Game"] = relationship(back_populates="daily_challenges")  # noqa: F821
    question_set: Mapped["QuestionSet"] = relationship(back_populates="daily_challenges")  # noqa: F821

    def __repr__(self) -> str:
        return f"<DailyChallenge game={self.game_id} date={self.challenge_date}>"
