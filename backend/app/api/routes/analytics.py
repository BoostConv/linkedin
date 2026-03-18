from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.post import Post
from app.models.analytics import PostAnalytics
from app.models.user import User
from app.api.routes.auth import get_current_user

router = APIRouter()


class AnalyticsSummary(BaseModel):
    total_posts: int
    total_impressions: int
    avg_engagement_rate: float
    total_comments: int
    total_likes: int
    best_post_id: UUID | None = None
    best_composite_score: float | None = None


@router.get("/summary", response_model=AnalyticsSummary)
async def get_summary(
    days: int = Query(default=30, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Count posts
    post_count = await db.execute(
        select(func.count(Post.id)).where(
            Post.user_id == current_user.id,
            Post.status == "published",
        )
    )
    total = post_count.scalar() or 0

    # Get latest analytics snapshots
    latest_analytics = await db.execute(
        select(PostAnalytics)
        .join(Post)
        .where(Post.user_id == current_user.id, PostAnalytics.snapshot_type == "7d")
        .order_by(PostAnalytics.composite_score.desc().nullslast())
    )
    snapshots = latest_analytics.scalars().all()

    total_impressions = sum(s.impressions for s in snapshots)
    total_comments = sum(s.comments for s in snapshots)
    total_likes = sum(s.likes for s in snapshots)
    avg_engagement = sum(s.engagement_rate for s in snapshots) / len(snapshots) if snapshots else 0.0
    best = snapshots[0] if snapshots else None

    return AnalyticsSummary(
        total_posts=total,
        total_impressions=total_impressions,
        avg_engagement_rate=round(avg_engagement, 4),
        total_comments=total_comments,
        total_likes=total_likes,
        best_post_id=best.post_id if best else None,
        best_composite_score=best.composite_score if best else None,
    )


@router.get("/posts/{post_id}")
async def get_post_analytics(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PostAnalytics)
        .join(Post)
        .where(Post.id == post_id, Post.user_id == current_user.id)
        .order_by(PostAnalytics.collected_at)
    )
    return result.scalars().all()
