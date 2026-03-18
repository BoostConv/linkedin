"""API routes for competitive intelligence."""
from uuid import UUID
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.competitor import Competitor, CompetitorPost
from app.models.pillar import Pillar
from app.api.routes.auth import get_current_user

router = APIRouter()


class CompetitorCreate(BaseModel):
    name: str
    linkedin_url: str


class CompetitorUpdate(BaseModel):
    name: str | None = None
    linkedin_url: str | None = None
    is_active: bool | None = None


@router.get("/")
async def list_competitors(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List all competitors."""
    result = await db.execute(select(Competitor).order_by(Competitor.name))
    competitors = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "linkedin_url": c.linkedin_url,
            "is_active": c.is_active,
            "created_at": c.created_at.isoformat(),
        }
        for c in competitors
    ]


@router.post("/")
async def create_competitor(
    data: CompetitorCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Add a new competitor to track."""
    comp = Competitor(name=data.name, linkedin_url=data.linkedin_url)
    db.add(comp)
    await db.commit()
    await db.refresh(comp)
    return {"id": str(comp.id), "name": comp.name, "linkedin_url": comp.linkedin_url}


@router.patch("/{competitor_id}/")
async def update_competitor(
    competitor_id: UUID,
    data: CompetitorUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Update a competitor."""
    result = await db.execute(select(Competitor).where(Competitor.id == competitor_id))
    comp = result.scalar_one_or_none()
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(comp, field, value)

    await db.commit()
    await db.refresh(comp)
    return {"id": str(comp.id), "name": comp.name, "linkedin_url": comp.linkedin_url, "is_active": comp.is_active}


@router.delete("/{competitor_id}/")
async def delete_competitor(
    competitor_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Delete a competitor."""
    result = await db.execute(select(Competitor).where(Competitor.id == competitor_id))
    comp = result.scalar_one_or_none()
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")

    await db.delete(comp)
    await db.commit()
    return {"status": "deleted"}


@router.get("/{competitor_id}/posts/")
async def list_competitor_posts(
    competitor_id: UUID,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get scraped posts for a competitor."""
    result = await db.execute(
        select(CompetitorPost)
        .where(CompetitorPost.competitor_id == competitor_id)
        .order_by(desc(CompetitorPost.scraped_at))
        .limit(limit)
    )
    posts = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "content": p.content[:200],
            "full_content": p.content,
            "post_type": p.post_type,
            "likes": p.likes,
            "comments": p.comments,
            "shares": p.shares,
            "detected_topic": p.detected_topic,
            "detected_template": p.detected_template,
            "relevance_score": p.relevance_score,
            "analysis": p.analysis,
            "posted_at": p.posted_at.isoformat() if p.posted_at else None,
            "scraped_at": p.scraped_at.isoformat(),
        }
        for p in posts
    ]


@router.get("/trends/")
async def get_trends(
    days: int = 14,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get trending topics from competitor posts."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(CompetitorPost)
        .where(CompetitorPost.scraped_at >= cutoff)
        .order_by(desc(CompetitorPost.scraped_at))
    )
    posts = result.scalars().all()

    # Group by detected topic
    topic_data = {}
    for p in posts:
        topic = (p.detected_topic or "").lower().strip()
        if not topic:
            continue
        if topic not in topic_data:
            topic_data[topic] = {
                "count": 0,
                "total_likes": 0,
                "total_comments": 0,
                "relevance_scores": [],
            }
        topic_data[topic]["count"] += 1
        topic_data[topic]["total_likes"] += p.likes
        topic_data[topic]["total_comments"] += p.comments
        if p.relevance_score:
            topic_data[topic]["relevance_scores"].append(p.relevance_score)

    trends = []
    for topic, data in topic_data.items():
        avg_relevance = (
            sum(data["relevance_scores"]) / len(data["relevance_scores"])
            if data["relevance_scores"]
            else 0
        )
        trends.append({
            "topic": topic,
            "post_count": data["count"],
            "total_engagement": data["total_likes"] + data["total_comments"],
            "avg_relevance": round(avg_relevance, 2),
            "trend_score": round(data["count"] * 0.5 + avg_relevance * 0.5, 2),
        })

    return sorted(trends, key=lambda x: x["trend_score"], reverse=True)[:20]


@router.get("/top-posts/")
async def get_top_posts(
    days: int = 14,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get top performing competitor posts, sorted by engagement."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(CompetitorPost, Competitor.name)
        .join(Competitor, CompetitorPost.competitor_id == Competitor.id)
        .where(CompetitorPost.scraped_at >= cutoff)
        .order_by(desc(CompetitorPost.likes + CompetitorPost.comments))
        .limit(limit)
    )
    rows = result.all()

    return [
        {
            "id": str(p.id),
            "competitor_name": comp_name,
            "content": p.content[:200],
            "likes": p.likes,
            "comments": p.comments,
            "shares": p.shares,
            "detected_topic": p.detected_topic,
            "detected_template": p.detected_template,
            "relevance_score": p.relevance_score,
            "posted_at": p.posted_at.isoformat() if p.posted_at else None,
        }
        for p, comp_name in rows
    ]
