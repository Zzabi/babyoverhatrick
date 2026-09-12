from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    clerk_user_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="user")  # user | admin

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships
    sessions: Mapped[list["PlayerSession"]] = relationship(back_populates="user")  # noqa: F821
    streaks: Mapped[list["Streak"]] = relationship(back_populates="user")  # noqa: F821
    leaderboard_entries: Mapped[list["LeaderboardEntry"]] = relationship(back_populates="user")  # noqa: F821

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
