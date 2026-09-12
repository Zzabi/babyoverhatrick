from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.models.base import Base


class Cricketer(Base):
    """
    Master list of known cricketers — used for autocomplete in Guess the Cricketer.
    Separate from the questions table: this is just the searchable name pool.
    Adding a cricketer here makes them available in the dropdown; it does NOT
    automatically create a game question.
    """
    __tablename__ = "cricketers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)  # ISO 3166 e.g. IND, AUS
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Cricketer name={self.name} country={self.country}>"
