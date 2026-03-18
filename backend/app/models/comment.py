import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("posts.id"))

    # LinkedIn data
    linkedin_comment_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    author_name: Mapped[str] = mapped_column(String(255))
    author_linkedin_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_headline: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text)

    # Reply management
    suggested_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    reply_status: Mapped[str] = mapped_column(String(20), default="pending")  # "pending", "suggested", "approved", "sent", "skipped"
    linkedin_reply_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Prioritization
    is_prospect: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[str] = mapped_column(String(10), default="normal")  # "high", "normal", "low"

    commented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    post: Mapped["Post"] = relationship()
