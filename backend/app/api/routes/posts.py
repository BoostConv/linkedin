from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.post import Post
from app.models.pillar import Pillar
from app.models.template import PostTemplate
from app.models.user import User
from app.api.routes.auth import get_current_user

router = APIRouter()


class PostCreate(BaseModel):
    content: str
    format: str = "text"
    pillar_id: UUID | None = None
    template_id: UUID | None = None
    idea_id: UUID | None = None
    hook_pattern: str | None = None
    cta_type: str | None = None
    image_url: str | None = None
    scheduled_at: datetime | None = None


class PostUpdate(BaseModel):
    content: str | None = None
    status: str | None = None
    scheduled_at: datetime | None = None
    image_url: str | None = None


class PostResponse(BaseModel):
    id: UUID
    content: str
    hook: str | None = None
    format: str
    pillar_id: UUID | None = None
    template_id: UUID | None = None
    pillar_name: str | None = None
    template_name: str | None = None
    idea_id: UUID | None = None
    hook_pattern: str | None = None
    cta_type: str | None = None
    word_count: int | None = None
    image_url: str | None = None
    carousel_url: str | None = None
    status: str
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    anti_ai_score: int | None = None
    anti_ai_issues: list | dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[PostResponse])
async def list_posts(
    status: str | None = None,
    pillar_id: UUID | None = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(
            Post,
            Pillar.name.label("pillar_name"),
            PostTemplate.name.label("template_name"),
        )
        .outerjoin(Pillar, Post.pillar_id == Pillar.id)
        .outerjoin(PostTemplate, Post.template_id == PostTemplate.id)
        .where(Post.user_id == current_user.id)
    )
    if status:
        query = query.where(Post.status == status)
    if pillar_id:
        query = query.where(Post.pillar_id == pillar_id)
    query = query.order_by(Post.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    posts = []
    for post, p_name, t_name in rows:
        post_dict = PostResponse.model_validate(post).model_dump()
        post_dict["pillar_name"] = p_name
        post_dict["template_name"] = t_name
        posts.append(PostResponse(**post_dict))
    return posts


@router.post("/", response_model=PostResponse, status_code=201)
async def create_post(
    data: PostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hook = data.content.split("\n")[0][:200] if data.content else None
    word_count = len(data.content.split()) if data.content else 0

    post = Post(
        user_id=current_user.id,
        content=data.content,
        hook=hook,
        format=data.format,
        pillar_id=data.pillar_id,
        template_id=data.template_id,
        idea_id=data.idea_id,
        hook_pattern=data.hook_pattern,
        cta_type=data.cta_type,
        word_count=word_count,
        image_url=data.image_url,
        status="scheduled" if data.scheduled_at else "draft",
        scheduled_at=data.scheduled_at,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


@router.get("/{post_id}/", response_model=PostResponse)
async def get_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Post).where(Post.id == post_id, Post.user_id == current_user.id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.patch("/{post_id}/", response_model=PostResponse)
async def update_post(
    post_id: UUID,
    data: PostUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Post).where(Post.id == post_id, Post.user_id == current_user.id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(post, field, value)

    if data.content:
        post.hook = data.content.split("\n")[0][:200]
        post.word_count = len(data.content.split())

    await db.commit()
    await db.refresh(post)
    return post


@router.delete("/{post_id}/", status_code=204)
async def delete_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Post).where(Post.id == post_id, Post.user_id == current_user.id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    await db.delete(post)
    await db.commit()
