import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class WritingRule(Base):
    __tablename__ = "writing_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category: Mapped[str] = mapped_column(String(50))  # "tone", "anti_ai", "banned_words", "hook_pattern", "cta"
    name: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)  # The rule itself
    example_good: Mapped[str | None] = mapped_column(Text, nullable=True)
    example_bad: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="error")  # "error" (blocks publish) or "warning"
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
