"""Celery task for weekly ML model retraining."""
import asyncio

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.tasks import celery_app
from app.config import get_settings

settings = get_settings()


@celery_app.task(name="app.tasks.ml_trainer.retrain_model")
def retrain_model():
    """Retrain the performance prediction model on all historical data."""
    from app.services.ml.model import train_model

    async def _run():
        engine = create_async_engine(settings.database_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as db:
            result = await train_model(db)
        await engine.dispose()
        return result

    result = asyncio.run(_run())
    return f"Model training: {result.get('status', 'unknown')} — {result.get('sample_count', 0)} samples"
