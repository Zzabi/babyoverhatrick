from sqlalchemy import String, Text, Integer, Boolean, DateTime, func, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.models.base import Base


class QuestionSet(Base):
    """
    A deck of questions for a game (e.g. 'IPL Legends', 'World Cup 2023').
    Content team creates sets via Admin CMS. No code deploy needed.
    """
    __tablename__ = "question_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty_default: Mapped[str] = mapped_column(String(20), default="medium")  # easy | medium | hard
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    is_daily_eligible: Mapped[bool] = mapped_column(Boolean, default=True)  # can be picked as daily challenge

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # relationships
    game: Mapped["Game"] = relationship(back_populates="question_sets")  # noqa: F821
    questions: Mapped[list["Question"]] = relationship(back_populates="question_set")
    daily_challenges: Mapped[list["DailyChallenge"]] = relationship(back_populates="question_set")  # noqa: F821

    def __repr__(self) -> str:
        return f"<QuestionSet id={self.id} name={self.name}>"


class Question(Base):
    """
    A single prompt within a set.
    question_type drives how the frontend renders it and how answers are evaluated.
    accepted_aliases handles name variants (e.g. 'R Ashwin' == 'Ravichandran Ashwin').
    """
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    set_id: Mapped[int] = mapped_column(ForeignKey("question_sets.id"), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)

    question_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # null for image-only prompts
    question_type: Mapped[str] = mapped_column(String(50))
    # question_type values: 'multiple_choice' | 'image_guess' | 'unscramble' | 'emoji_guess'

    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")
    points: Mapped[int] = mapped_column(Integer, default=100)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)  # shown after reveal
    accepted_aliases: Mapped[list] = mapped_column(JSONB, default=list)
    # e.g. ["R Ashwin", "Ravichandran Ashwin", "Ashwin"] — all accepted as correct

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships
    question_set: Mapped["QuestionSet"] = relationship(back_populates="questions")
    options: Mapped[list["QuestionOption"]] = relationship(back_populates="question", cascade="all, delete-orphan")
    game_answers: Mapped[list["GameAnswer"]] = relationship(back_populates="question")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Question id={self.id} type={self.question_type}>"


class QuestionOption(Base):
    """
    Answer choices for multiple-choice questions.
    For other question types, options hold the correct answer only (is_correct=True).
    """
    __tablename__ = "question_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    option_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    option_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # relationships
    question: Mapped["Question"] = relationship(back_populates="options")

    def __repr__(self) -> str:
        return f"<QuestionOption id={self.id} correct={self.is_correct}>"
