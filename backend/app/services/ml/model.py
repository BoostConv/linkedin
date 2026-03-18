"""ML model for predicting post performance.

Uses GradientBoosting from scikit-learn, retrained weekly.
Model is persisted to database (brand_config table) and loaded at prediction time.
"""
import json
import pickle
from datetime import datetime, timezone

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.models.analytics import PostAnalytics
from app.services.ml.features import extract_features, FEATURE_NAMES

# In-memory cache to avoid reloading from DB on every prediction
_model_cache = {"model": None, "meta": None, "loaded_at": None}


async def _load_model_from_db(db: AsyncSession):
    """Load model from database into cache."""
    result = await db.execute(
        text("SELECT model_data, meta FROM ml_models ORDER BY trained_at DESC LIMIT 1")
    )
    row = result.first()
    if row and row[0]:
        _model_cache["model"] = pickle.loads(row[0])
        _model_cache["meta"] = row[1] if row[1] else {}
        _model_cache["loaded_at"] = datetime.now(timezone.utc)
        return True
    return False


async def _save_model_to_db(db: AsyncSession, model, meta: dict):
    """Save model to database."""
    model_bytes = pickle.dumps(model)
    await db.execute(text("DELETE FROM ml_models"))
    await db.execute(
        text("INSERT INTO ml_models (model_data, meta) VALUES (:model_data, :meta)"),
        {"model_data": model_bytes, "meta": json.dumps(meta)},
    )
    await db.commit()
    # Update cache
    _model_cache["model"] = model
    _model_cache["meta"] = meta
    _model_cache["loaded_at"] = datetime.now(timezone.utc)


async def train_model(db: AsyncSession) -> dict:
    """Train the performance prediction model on all published posts with analytics.

    Returns metadata about the training run.
    """
    from sklearn.ensemble import GradientBoostingRegressor
    from sqlalchemy import select

    # Fetch posts with 24h analytics (our target metric)
    result = await db.execute(
        select(Post, PostAnalytics)
        .join(PostAnalytics, PostAnalytics.post_id == Post.id)
        .where(
            Post.status == "published",
            PostAnalytics.snapshot_type == "24h",
        )
    )
    rows = result.all()

    if len(rows) < 10:
        return {"status": "insufficient_data", "sample_count": len(rows), "min_required": 10}

    # Build feature matrix and target vector
    X = []
    y = []
    for post, analytics in rows:
        post_data = {
            "content": post.content,
            "format": post.format,
            "hook_pattern": post.hook_pattern,
            "cta_type": post.cta_type,
            "scheduled_at": post.scheduled_at or post.published_at,
            "anti_ai_score": post.anti_ai_score,
        }
        features = extract_features(post_data)
        feature_vector = [features.get(name, 0) for name in FEATURE_NAMES]
        X.append(feature_vector)
        y.append(analytics.composite_score or 0)

    X = np.array(X)
    y = np.array(y)

    # Normalize target by z-score
    y_mean = float(np.mean(y))
    y_std = float(np.std(y)) if np.std(y) > 0 else 1.0
    y_norm = (y - y_mean) / y_std

    # Train model
    model = GradientBoostingRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        random_state=42,
    )
    model.fit(X, y_norm)

    # Save metadata
    feature_importances = dict(zip(FEATURE_NAMES, model.feature_importances_.tolist()))
    top_features = sorted(feature_importances.items(), key=lambda x: x[1], reverse=True)[:10]

    meta = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "sample_count": len(rows),
        "y_mean": y_mean,
        "y_std": y_std,
        "train_score": float(model.score(X, y_norm)),
        "top_features": top_features,
    }

    # Save to database
    await _save_model_to_db(db, model, meta)

    return {"status": "trained", **meta}


async def predict_score(db: AsyncSession, post_data: dict) -> float | None:
    """Predict the performance score for a post.

    Returns None if model is not trained yet.
    """
    # Load from DB if not in cache
    if _model_cache["model"] is None:
        loaded = await _load_model_from_db(db)
        if not loaded:
            return None

    model = _model_cache["model"]
    meta = _model_cache["meta"]

    if not model or not meta:
        return None

    features = extract_features(post_data)
    feature_vector = [features.get(name, 0) for name in FEATURE_NAMES]
    X = np.array([feature_vector])

    # Predict normalized score, then denormalize
    y_pred_norm = model.predict(X)[0]
    y_pred = y_pred_norm * meta.get("y_std", 1) + meta.get("y_mean", 0)

    return round(float(y_pred), 2)


async def get_model_meta(db: AsyncSession) -> dict | None:
    """Get metadata about the current trained model."""
    if _model_cache["meta"] is None:
        await _load_model_from_db(db)
    return _model_cache["meta"]
