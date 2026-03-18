import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class PostTemplate(Base):
    __tablename__ = "post_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True)  # e.g. "L'effet Google (GAFAM)"
    slug: Mapped[str] = mapped_column(String(100), unique=True)  # e.g. "gafam"
    description: Mapped[str] = mapped_column(Text)
    structure: Mapped[dict] = mapped_column(JSONB)  # Steps of the template as structured data
    example_posts: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # URLs + content of example posts
    prompt_instructions: Mapped[str] = mapped_column(Text)  # Detailed instructions for Claude
    when_to_use: Mapped[str] = mapped_column(Text)  # Guidance on when this template fits
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
