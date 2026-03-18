import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class Product(Base):
    """Products/services offered by Boost Conversion.

    Used by the AI to generate posts that promote specific offerings
    (e.g., Benchmark GA4, NeuroCRO Score, Quiz Funnels, etc.)
    """
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True)  # e.g. "NeuroCRO Score"
    slug: Mapped[str] = mapped_column(String(100), unique=True)  # e.g. "neurocro-score"
    tagline: Mapped[str] = mapped_column(String(500))  # One-liner description
    description: Mapped[str] = mapped_column(Text)  # Full description for AI context
    target_audience: Mapped[str] = mapped_column(Text)  # Who is this for?
    key_benefits: Mapped[dict] = mapped_column(JSONB, default=list)  # List of benefits
    pain_points: Mapped[dict] = mapped_column(JSONB, default=list)  # Pain points it solves
    proof_points: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Stats, case studies, etc.
    cta_text: Mapped[str | None] = mapped_column(String(500), nullable=True)  # Default CTA for this product
    price_info: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Price/positioning info
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)  # Link to product page
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
