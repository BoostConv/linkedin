from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "linkedin_automation",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    timezone="Europe/Paris",
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    beat_schedule={
        "publish-scheduled-posts": {
            "task": "app.tasks.publisher.publish_scheduled_posts",
            "schedule": 60.0,  # Check every minute
        },
        "collect-analytics-2h": {
            "task": "app.tasks.analytics_collector.collect_analytics",
            "schedule": 7200.0,  # Every 2 hours
            "args": ["2h"],
        },
        "collect-analytics-24h": {
            "task": "app.tasks.analytics_collector.collect_analytics",
            "schedule": 86400.0,  # Every 24 hours
            "args": ["24h"],
        },
        "retrain-ml-model": {
            "task": "app.tasks.ml_trainer.retrain_model",
            "schedule": 604800.0,  # Every 7 days
        },
        "scrape-competitors": {
            "task": "app.tasks.competitor_scraper.scrape_competitors",
            "schedule": 86400.0,  # Every 24 hours
        },
    },
)

celery_app.autodiscover_tasks(["app.tasks"])
