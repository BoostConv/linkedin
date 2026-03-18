from datetime import datetime, date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.post import Post
from app.models.user import User
from app.api.routes.auth import get_current_user
from app.services.ai.smart_calendar import generate_content_plan, regenerate_day

router = APIRouter()


class CalendarEvent(BaseModel):
    id: UUID
    title: str  # First 80 chars of content
    status: str
    format: str
    pillar_id: UUID | None = None
    scheduled_at: datetime | None = None
    published_at: datetime | None = None

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[CalendarEvent])
async def get_calendar(
    start: date = Query(...),
    end: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Post)
        .where(
            Post.user_id == current_user.id,
            Post.status.in_(["scheduled", "published", "approved"]),
            Post.scheduled_at.isnot(None),
            Post.scheduled_at >= datetime.combine(start, datetime.min.time()),
            Post.scheduled_at <= datetime.combine(end, datetime.max.time()),
        )
        .order_by(Post.scheduled_at)
    )
    posts = result.scalars().all()

    return [
        CalendarEvent(
            id=p.id,
            title=p.content[:80] + "..." if len(p.content) > 80 else p.content,
            status=p.status,
            format=p.format,
            pillar_id=p.pillar_id,
            scheduled_at=p.scheduled_at,
            published_at=p.published_at,
        )
        for p in posts
    ]


class ContentPlanRequest(BaseModel):
    days: int = 7


class RegenerateDayRequest(BaseModel):
    date: str  # YYYY-MM-DD
    constraints: str | None = None


@router.post("/generate-plan")
async def generate_plan(
    data: ContentPlanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Auto-generate a content plan for the next N days."""
    plan = await generate_content_plan(db, current_user.id, days=data.days)
    return plan


@router.post("/regenerate-day")
async def regenerate_day_endpoint(
    data: RegenerateDayRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Regenerate the plan for a single day with optional constraints."""
    result = await regenerate_day(
        db, current_user.id, data.date, data.constraints
    )
    return result
