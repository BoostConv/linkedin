import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Idea(Base):
    __tablename__ = "ideas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Input from Sébastien
    input_type: Mapped[str] = mapped_column(String(50))  # "url", "raw_idea", "repost", "theme_list"
    raw_input: Mapped[str] = mapped_column(Text)  # The original input (URL, text, etc.)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    scraped_content: Mapped[str | None] = mapped_column(Text, nullable=True)  # Content scraped from URL

    # AI analysis
    suggested_pillar_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("pillars.id"), nullable=True)
    suggested_template_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("post_templates.id"), nullable=True)
    suggested_angle: Mapped[str | None] = mapped_column(Text, nullable=True)  # AI-suggested angle/approach
    priority: Mapped[str] = mapped_column(String(20), default="medium")  # "high", "medium", "low"
    tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Auto-generated tags

    # Status
    status: Mapped[str] = mapped_column(String(20), default="new")  # "new", "drafting", "planned", "published", "archived"

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="ideas")
