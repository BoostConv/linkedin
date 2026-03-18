"""Branding / charte graphique configuration for carousels and visuals."""
import json
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models.user import User
from app.api.routes.auth import get_current_user

router = APIRouter()

BRAND_CONFIG_PATH = Path("/app/brand_config.json")

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


def _load_brand_config() -> dict:
    if BRAND_CONFIG_PATH.exists():
        try:
            return json.loads(BRAND_CONFIG_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_BRAND)


def _save_brand_config(config: dict):
    BRAND_CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False))


@router.get("/", response_model=BrandConfigResponse)
async def get_brand_config(
    _: User = Depends(get_current_user),
):
    """Get current brand configuration."""
    return BrandConfigResponse(**_load_brand_config())


@router.patch("/", response_model=BrandConfigResponse)
async def update_brand_config(
    data: BrandConfigUpdate,
    _: User = Depends(get_current_user),
):
    """Update brand configuration."""
    config = _load_brand_config()
    update_data = data.model_dump(exclude_unset=True)
    config.update(update_data)
    _save_brand_config(config)
    return BrandConfigResponse(**config)


@router.post("/reset", response_model=BrandConfigResponse)
async def reset_brand_config(
    _: User = Depends(get_current_user),
):
    """Reset brand config to defaults (Charte Graphique Boost Conversion)."""
    _save_brand_config(dict(DEFAULT_BRAND))
    return BrandConfigResponse(**DEFAULT_BRAND)
