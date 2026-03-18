"""API routes for ML model insights and recommendations."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.api.routes.auth import get_current_user
from app.services.ml.model import train_model, predict_score, get_model_meta
from app.services.ml.recommendations import get_recommendations

router = APIRouter()


@router.get("/recommendations/")
async def recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get ML-based content recommendations."""
    return await get_recommendations(db, current_user.id)


@router.post("/predict/")
async def predict(
    content: str,
    format: str = "text",
    hook_pattern: str | None = None,
    cta_type: str | None = None,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Predict performance score for a post."""
    score = await predict_score(db, {
        "content": content,
        "format": format,
        "hook_pattern": hook_pattern,
        "cta_type": cta_type,
    })
    if score is None:
        return {"predicted_score": None, "message": "Modèle pas encore entraîné. Publiez plus de posts."}
    return {"predicted_score": score}


@router.get("/model-info/")
async def model_info(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get information about the current ML model."""
    meta = await get_model_meta(db)
    if not meta:
        return {"status": "not_trained", "message": "Aucun modèle entraîné."}
    return {"status": "trained", **meta}


@router.post("/retrain/")
async def retrain(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Manually trigger model retraining."""
    result = await train_model(db)
    return result
