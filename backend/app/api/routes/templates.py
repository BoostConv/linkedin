from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.template import PostTemplate
from app.models.user import User
from app.api.routes.auth import get_current_user

router = APIRouter()


class TemplateCreate(BaseModel):
    name: str
    slug: str
    description: str
    structure: dict
    example_posts: dict | None = None
    prompt_instructions: str
    when_to_use: str
    display_order: int = 0


class TemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    structure: dict | None = None
    example_posts: dict | None = None
    prompt_instructions: str | None = None
    when_to_use: str | None = None
    display_order: int | None = None
    is_active: bool | None = None


class TemplateResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str
    structure: dict
    example_posts: dict | None = None
    prompt_instructions: str
    when_to_use: str
    display_order: int
    is_active: bool

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[TemplateResponse])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(PostTemplate).order_by(PostTemplate.display_order))
    return result.scalars().all()


@router.post("/", response_model=TemplateResponse, status_code=201)
async def create_template(
    data: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    template = PostTemplate(**data.model_dump())
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.get("/{template_id}/", response_model=TemplateResponse)
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(PostTemplate).where(PostTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.patch("/{template_id}/", response_model=TemplateResponse)
async def update_template(
    template_id: UUID,
    data: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(PostTemplate).where(PostTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)
    return template
