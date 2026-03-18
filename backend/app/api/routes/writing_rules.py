from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.writing_rule import WritingRule
from app.models.user import User
from app.api.routes.auth import get_current_user

router = APIRouter()


class WritingRuleCreate(BaseModel):
    category: str
    name: str
    content: str
    example_good: str | None = None
    example_bad: str | None = None
    severity: str = "error"
    display_order: int = 0


class WritingRuleUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    example_good: str | None = None
    example_bad: str | None = None
    severity: str | None = None
    display_order: int | None = None
    is_active: bool | None = None


class WritingRuleResponse(BaseModel):
    id: UUID
    category: str
    name: str
    content: str
    example_good: str | None = None
    example_bad: str | None = None
    severity: str
    display_order: int
    is_active: bool

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[WritingRuleResponse])
async def list_rules(
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(WritingRule).order_by(WritingRule.display_order)
    if category:
        query = query.where(WritingRule.category == category)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=WritingRuleResponse, status_code=201)
async def create_rule(
    data: WritingRuleCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rule = WritingRule(**data.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.patch("/{rule_id}", response_model=WritingRuleResponse)
async def update_rule(
    rule_id: UUID,
    data: WritingRuleUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(WritingRule).where(WritingRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(WritingRule).where(WritingRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    await db.delete(rule)
    await db.commit()
