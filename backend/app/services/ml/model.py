"""ML model for predicting post performance.

Uses GradientBoosting from scikit-learn, retrained weekly.
Model is persisted to disk and loaded at prediction time.
"""
import json
import os
import pickle
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.models.analytics import PostAnalytics
from app.services.ml.features import extract_features, FEATURE_NAMES

MODEL_DIR = Path("ml_models")
MODEL_PATH = MODEL_DIR / "performance_model.pkl"
META_PATH = MODEL_DIR / "model_meta.json"


async def train_model(db: AsyncSession) -> dict:
    """Train the performance prediction model on all published posts with analytics.

    Returns metadata about the training run.
    """
    from sklearn.ensemble import GradientBoostingRegressor

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

    # Save model
    MODEL_DIR.mkdir(exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

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
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)

    return {"status": "trained", **meta}


def predict_score(post_data: dict) -> float | None:
    """Predict the performance score for a post.

    Returns None if model is not trained yet.
    """
    if not MODEL_PATH.exists() or not META_PATH.exists():
        return None

    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)

    with open(META_PATH) as f:
        meta = json.load(f)

    features = extract_features(post_data)
    feature_vector = [features.get(name, 0) for name in FEATURE_NAMES]
    X = np.array([feature_vector])

    # Predict normalized score, then denormalize
    y_pred_norm = model.predict(X)[0]
    y_pred = y_pred_norm * meta["y_std"] + meta["y_mean"]

    return round(float(y_pred), 2)


def get_model_meta() -> dict | None:
    """Get metadata about the current trained model."""
    if not META_PATH.exists():
        return None
    with open(META_PATH) as f:
        return json.load(f)
