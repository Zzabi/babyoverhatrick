from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.models.base import Base


class ShareEvent(Base):
    """
    Tracks when and where a player shared their result card.
    Powers the share funnel analytics (share_initiated → share_completed).
    """
    __tablename__ = "share_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("player_sessions.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    share_channel: Mapped[str] = mapped_column(String(50))
    # values: 'instagram_story' | 'whatsapp' | 'copy_link' | 'twitter' | 'other'

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # relationships
    session: Mapped["PlayerSession"] = relationship(back_populates="share_events")  # noqa: F821

    def __repr__(self) -> str:
        return f"<ShareEvent session={self.session_id} channel={self.share_channel}>"
