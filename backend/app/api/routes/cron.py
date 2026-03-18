"""Cron job endpoints — replaces Celery tasks.

Protected by CRON_SECRET header for Vercel Cron Jobs.
"""
import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.post import Post
from app.models.analytics import PostAnalytics
from app.models.user import User
from app.models.competitor import Competitor, CompetitorPost
from app.models.pillar import Pillar

logger = logging.getLogger(__name__)
router = APIRouter()

CRON_SECRET = os.environ.get("CRON_SECRET", "")

SNAPSHOT_WINDOWS = {
    "2h": timedelta(hours=2),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "48h": timedelta(hours=48),
    "7d": timedelta(days=7),
}


def _verify_cron_secret(request: Request):
    """Verify the request comes from Vercel Cron or has valid secret."""
    if not CRON_SECRET:
        return  # No secret configured, allow all (dev mode)
    auth = request.headers.get("authorization", "")
    if auth != f"Bearer {CRON_SECRET}":
        raise HTTPException(status_code=401, detail="Invalid cron secret")


@router.post("/publish/")
async def cron_publish(request: Request):
    """Publish scheduled posts that are due."""
    _verify_cron_secret(request)
    from app.services.linkedin.publisher import publish_text_post, publish_image_post

    now = datetime.now(timezone.utc)
    published = 0

    async with async_session() as db:
        result = await db.execute(
            select(Post).where(
                Post.status == "scheduled",
                Post.scheduled_at <= now,
            ).limit(5)  # Max 5 per invocation to stay within timeout
        )
        posts = list(result.scalars().all())

        for post in posts:
            user_result = await db.execute(
                select(User).where(User.id == post.user_id)
            )
            user = user_result.scalar_one_or_none()
            if not user or not user.linkedin_access_token or not user.linkedin_person_id:
                post.status = "failed"
                await db.commit()
                continue

            try:
                if post.image_url:
                    pub_result = await publish_image_post(
                        access_token=user.linkedin_access_token,
                        person_id=user.linkedin_person_id,
                        content=post.content,
                        image_url=post.image_url,
                    )
                else:
                    pub_result = await publish_text_post(
                        access_token=user.linkedin_access_token,
                        person_id=user.linkedin_person_id,
                        content=post.content,
                    )
                post.linkedin_post_id = pub_result["linkedin_post_id"]
                post.status = "published"
                post.published_at = datetime.now(timezone.utc)
                published += 1
            except Exception as e:
                logger.error(f"Failed to publish post {post.id}: {e}")
                post.status = "failed"
                if not post.generation_metadata:
                    post.generation_metadata = {}
                post.generation_metadata["publish_error"] = str(e)

            await db.commit()

    return {"published": published, "checked": len(posts)}


@router.post("/analytics/")
async def cron_analytics(request: Request, snapshot: str = "24h"):
    """Collect analytics for published posts matching the snapshot window."""
    _verify_cron_secret(request)
    from app.services.linkedin.analytics import get_post_stats

    window = SNAPSHOT_WINDOWS.get(snapshot)
    if not window:
        raise HTTPException(status_code=400, detail=f"Unknown snapshot type: {snapshot}")

    now = datetime.now(timezone.utc)
    window_start = now - window - timedelta(hours=1)
    window_end = now - window + timedelta(hours=1)
    collected = 0

    async with async_session() as db:
        result = await db.execute(
            select(Post).where(
                Post.status == "published",
                Post.published_at.isnot(None),
                Post.published_at >= window_start,
                Post.published_at <= window_end,
            )
        )
        posts = list(result.scalars().all())

        for post in posts:
            # Check if snapshot already exists
            existing = await db.execute(
                select(PostAnalytics).where(
                    PostAnalytics.post_id == post.id,
                    PostAnalytics.snapshot_type == snapshot,
                )
            )
            if existing.scalar_one_or_none():
                continue

            user_result = await db.execute(
                select(User).where(User.id == post.user_id)
            )
            user = user_result.scalar_one_or_none()
            if not user or not user.linkedin_access_token or not post.linkedin_post_id:
                continue

            try:
                stats = await get_post_stats(
                    access_token=user.linkedin_access_token,
                    linkedin_post_id=post.linkedin_post_id,
                )
                composite = (
                    0.25 * stats["impressions"]
                    + 0.35 * stats["engagement_rate"] * 10000
                    + 0.25 * stats["comments"] * 100
                    + 0.15 * stats["clicks"] * 10
                )
                analytics = PostAnalytics(
                    post_id=post.id,
                    snapshot_type=snapshot,
                    impressions=stats["impressions"],
                    likes=stats["likes"],
                    comments=stats["comments"],
                    shares=stats["shares"],
                    clicks=stats["clicks"],
                    engagement_rate=stats["engagement_rate"],
                    composite_score=round(composite, 2),
                )
                db.add(analytics)
                await db.commit()
                collected += 1
            except Exception as e:
                logger.error(f"Error collecting analytics for post {post.id}: {e}")

    return {"collected": collected, "checked": len(posts), "snapshot": snapshot}


@router.post("/retrain/")
async def cron_retrain(request: Request):
    """Retrain the ML performance prediction model."""
    _verify_cron_secret(request)
    from app.services.ml.model import train_model

    async with async_session() as db:
        result = await train_model(db)

    return result


@router.post("/scrape/")
async def cron_scrape(request: Request):
    """Scrape competitor posts and analyze them."""
    _verify_cron_secret(request)
    from app.services.competitors.scraper import scrape_competitor_posts
    from app.services.competitors.analyzer import analyze_competitor_posts

    total_saved = 0

    async with async_session() as db:
        comp_result = await db.execute(
            select(Competitor).where(Competitor.is_active.is_(True))
        )
        competitors = list(comp_result.scalars().all())

        pillar_result = await db.execute(
            select(Pillar).where(Pillar.is_active.is_(True))
        )
        pillar_names = [p.name for p in pillar_result.scalars().all()]

    for comp in competitors:
        try:
            posts = await scrape_competitor_posts(comp.linkedin_url, max_posts=10)
            if not posts:
                continue

            analyses = await analyze_competitor_posts(posts, pillar_names)

            async with async_session() as db:
                for i, post_data in enumerate(posts):
                    if post_data.get("post_url"):
                        existing = await db.execute(
                            select(CompetitorPost).where(
                                CompetitorPost.linkedin_post_url == post_data["post_url"]
                            )
                        )
                        if existing.scalar_one_or_none():
                            continue

                    analysis = next((a for a in analyses if a.get("index") == i + 1), {})
                    cp = CompetitorPost(
                        competitor_id=comp.id,
                        linkedin_post_url=post_data.get("post_url"),
                        content=post_data.get("content", ""),
                        post_type=post_data.get("post_type"),
                        likes=post_data.get("likes", 0),
                        comments=post_data.get("comments", 0),
                        shares=post_data.get("shares", 0),
                        detected_topic=analysis.get("detected_topic"),
                        detected_template=analysis.get("detected_template"),
                        relevance_score=analysis.get("relevance_score"),
                        analysis={
                            "relevant_pillar": analysis.get("relevant_pillar"),
                            "key_insight": analysis.get("key_insight"),
                            "engagement_quality": analysis.get("engagement_quality"),
                        },
                        posted_at=(
                            datetime.fromisoformat(post_data["posted_at"].replace("Z", "+00:00"))
                            if post_data.get("posted_at")
                            else None
                        ),
                    )
                    db.add(cp)
                    total_saved += 1
                await db.commit()

        except Exception as e:
            logger.error(f"Error scraping {comp.name}: {e}")

    return {"scraped": total_saved, "competitors": len(competitors)}
