import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Content
    content: Mapped[str] = mapped_column(Text)
    hook: Mapped[str | None] = mapped_column(Text, nullable=True)  # Extracted first lines
    format: Mapped[str] = mapped_column(String(50), default="text")  # "text", "carousel", "image_text"
    pillar_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("pillars.id"), nullable=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("post_templates.id"), nullable=True)
    idea_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ideas.id"), nullable=True)

    # Generation metadata
    hook_pattern: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "contrarian", "data_bomb", etc.
    cta_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generation_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)  # The prompt used to generate
    generation_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Model, tokens, etc.

    # Visual
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    carousel_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Status & scheduling
    status: Mapped[str] = mapped_column(String(20), default="draft")  # "draft", "review", "approved", "scheduled", "published", "failed"
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    linkedin_post_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Anti-AI validation
    anti_ai_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0-100, higher = more human
    anti_ai_issues: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # List of detected issues

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="posts")
    analytics: Mapped[list["PostAnalytics"]] = relationship(back_populates="post", lazy="selectin")
