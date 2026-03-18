"""Celery task for collecting LinkedIn post analytics."""
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

from app.tasks import celery_app
from app.config import get_settings
from app.models.post import Post
from app.models.analytics import PostAnalytics
from app.models.user import User

settings = get_settings()

# Map snapshot types to how old the post should be
SNAPSHOT_WINDOWS = {
    "2h": timedelta(hours=2),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "48h": timedelta(hours=48),
    "7d": timedelta(days=7),
}


async def _collect_for_post(post_id: str, user_id: str, snapshot_type: str):
    """Collect analytics for a single post."""
    from app.services.linkedin.analytics import get_post_stats

    engine = create_engine(settings.database_url_sync)
    with Session(engine) as db:
        post = db.get(Post, post_id)
        user = db.get(User, user_id)

        if not post or not user or not post.linkedin_post_id:
            return

        if not user.linkedin_access_token:
            return

        try:
            stats = await get_post_stats(
                access_token=user.linkedin_access_token,
                linkedin_post_id=post.linkedin_post_id,
            )

            # Calculate composite score
            # score = 0.25*impressions_norm + 0.35*engagement_rate + 0.25*comments + 0.15*clicks
            # For now, use raw values (normalization happens in ML pipeline)
            composite = (
                0.25 * stats["impressions"]
                + 0.35 * stats["engagement_rate"] * 10000  # Scale engagement rate
                + 0.25 * stats["comments"] * 100  # Scale comments
                + 0.15 * stats["clicks"] * 10  # Scale clicks
            )

            analytics = PostAnalytics(
                post_id=post.id,
                snapshot_type=snapshot_type,
                impressions=stats["impressions"],
                likes=stats["likes"],
                comments=stats["comments"],
                shares=stats["shares"],
                clicks=stats["clicks"],
                engagement_rate=stats["engagement_rate"],
                composite_score=round(composite, 2),
            )
            db.add(analytics)
            db.commit()

        except Exception as e:
            print(f"Error collecting analytics for post {post_id}: {e}")


@celery_app.task(name="app.tasks.analytics_collector.collect_analytics")
def collect_analytics(snapshot_type: str = "24h"):
    """Collect analytics for all published posts that match the snapshot window."""
    engine = create_engine(settings.database_url_sync)
    now = datetime.now(timezone.utc)

    window = SNAPSHOT_WINDOWS.get(snapshot_type)
    if not window:
        return f"Unknown snapshot type: {snapshot_type}"

    with Session(engine) as db:
        # Find published posts that were published within the right window
        # For "2h" snapshot: posts published ~2 hours ago
        # For "7d" snapshot: posts published ~7 days ago
        window_start = now - window - timedelta(hours=1)  # 1 hour buffer
        window_end = now - window + timedelta(hours=1)

        posts = db.execute(
            select(Post).where(
                Post.status == "published",
                Post.published_at.isnot(None),
                Post.published_at >= window_start,
                Post.published_at <= window_end,
            )
        ).scalars().all()

        # Also check if we already have this snapshot
        for post in posts:
            existing = db.execute(
                select(PostAnalytics).where(
                    PostAnalytics.post_id == post.id,
                    PostAnalytics.snapshot_type == snapshot_type,
                )
            ).scalar_one_or_none()

            if not existing:
                asyncio.run(_collect_for_post(str(post.id), str(post.user_id), snapshot_type))

    return f"Collected {snapshot_type} analytics for {len(posts)} post(s)"
