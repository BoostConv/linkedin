"""Branding / charte graphique configuration for carousels and visuals."""
import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.api.routes.auth import get_current_user

router = APIRouter()

# Default brand config (Charte Graphique Boost Conversion)
DEFAULT_BRAND = {
    "primary_color": "#B97FE5",       # Science Purple
    "secondary_color": "#FFAD77",     # Orange Tonique
    "bg_color": "#FFFFFF",            # Blanc
    "text_color": "#311A4F",          # Bleu Sérieux
    "light_text_color": "#92ABFB",    # Bleu Ciel
    "accent_bg_color": "#F7F1FB",     # Fond Violet
    "highlight_color": "#3D55DF",     # Violet vif
    "author_name": "Sébastien Tortu",
    "author_title": "Fondateur @ Boost Conversion",
    "logo_text": "BOOST CONVERSION",
    "font_titles": "Helvetica Neue Bold",
    "font_body": "Helvetica Neue Regular",
}


class BrandConfigResponse(BaseModel):
    primary_color: str
    secondary_color: str
    bg_color: str
    text_color: str
    light_text_color: str
    accent_bg_color: str
    highlight_color: str
    author_name: str
    author_title: str
    logo_text: str
    font_titles: str
    font_body: str


class BrandConfigUpdate(BaseModel):
    primary_color: str | None = None
    secondary_color: str | None = None
    bg_color: str | None = None
    text_color: str | None = None
    light_text_color: str | None = None
    accent_bg_color: str | None = None
    highlight_color: str | None = None
    author_name: str | None = None
    author_title: str | None = None
    logo_text: str | None = None
    font_titles: str | None = None
    font_body: str | None = None


async def _load_brand_config(db: AsyncSession) -> dict:
    result = await db.execute(
        text("SELECT config FROM brand_config ORDER BY updated_at DESC LIMIT 1")
    )
    row = result.first()
    if row and row[0]:
        return {**DEFAULT_BRAND, **row[0]}
    return dict(DEFAULT_BRAND)


async def _save_brand_config(db: AsyncSession, config: dict):
    # Upsert: delete old rows and insert new one
    await db.execute(text("DELETE FROM brand_config"))
    await db.execute(
        text("INSERT INTO brand_config (config) VALUES (:config)"),
        {"config": json.dumps(config, ensure_ascii=False)},
    )
    await db.commit()


@router.get("/", response_model=BrandConfigResponse)
async def get_brand_config(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current brand configuration."""
    config = await _load_brand_config(db)
    return BrandConfigResponse(**config)


@router.patch("/", response_model=BrandConfigResponse)
async def update_brand_config(
    data: BrandConfigUpdate,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update brand configuration."""
    config = await _load_brand_config(db)
    update_data = data.model_dump(exclude_unset=True)
    config.update(update_data)
    await _save_brand_config(db, config)
    return BrandConfigResponse(**config)


@router.post("/reset", response_model=BrandConfigResponse)
async def reset_brand_config(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset brand config to defaults (Charte Graphique Boost Conversion)."""
    await _save_brand_config(db, dict(DEFAULT_BRAND))
    return BrandConfigResponse(**DEFAULT_BRAND)
