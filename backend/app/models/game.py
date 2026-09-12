from sqlalchemy import String, Text, DateTime, func, Integer, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.models.base import Base


class Game(Base):
    """
    A game type (e.g. 'guess-the-cricketer', 'unscramble-the-name').
    Config JSONB holds engine settings: rounds, timePerQuestion, scoring, hintPenalty, etc.
    Adding a new game = inserting a row + registering a UI component. No backend code change.
    """
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)  # e.g. 'guess-the-cricketer'
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | active | archived
    config: Mapped[dict] = mapped_column(JSONB, default=dict)  # rounds, timer, scoring, etc.
    version: Mapped[int] = mapped_column(Integer, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)  # controls homepage display order

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships
    question_sets: Mapped[list["QuestionSet"]] = relationship(back_populates="game")  # noqa: F821
    sessions: Mapped[list["PlayerSession"]] = relationship(back_populates="game")  # noqa: F821
    daily_challenges: Mapped[list["DailyChallenge"]] = relationship(back_populates="game")  # noqa: F821
    leaderboard_entries: Mapped[list["LeaderboardEntry"]] = relationship(back_populates="game")  # noqa: F821
    streaks: Mapped[list["Streak"]] = relationship(back_populates="game")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Game slug={self.slug} status={self.status}>"


class Category(Base):
    """
    Self-referential tree: Sports > Cricket > Batsmen
    Questions can belong to a category for filtering and grouping.
    """
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # self-ref FK added via FK constraint

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Category slug={self.slug}>"
