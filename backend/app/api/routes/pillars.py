from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.pillar import Pillar
from app.models.user import User
from app.api.routes.auth import get_current_user

router = APIRouter()


class PillarCreate(BaseModel):
    name: str
    description: str
    weight: float = 1.0
    preferred_templates: str | None = None
    display_order: int = 0


class PillarUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    weight: float | None = None
    preferred_templates: str | None = None
    display_order: int | None = None
    is_active: bool | None = None


class PillarResponse(BaseModel):
    id: UUID
    name: str
    description: str
    weight: float
    preferred_templates: str | None = None
    display_order: int
    is_active: bool

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[PillarResponse])
async def list_pillars(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Pillar).order_by(Pillar.display_order))
    return result.scalars().all()


@router.post("/", response_model=PillarResponse, status_code=201)
async def create_pillar(
    data: PillarCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    pillar = Pillar(**data.model_dump())
    db.add(pillar)
    await db.commit()
    await db.refresh(pillar)
    return pillar


@router.patch("/{pillar_id}", response_model=PillarResponse)
async def update_pillar(
    pillar_id: UUID,
    data: PillarUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Pillar).where(Pillar.id == pillar_id))
    pillar = result.scalar_one_or_none()
    if not pillar:
        raise HTTPException(status_code=404, detail="Pillar not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(pillar, field, value)

    await db.commit()
    await db.refresh(pillar)
    return pillar


@router.delete("/{pillar_id}", status_code=204)
async def delete_pillar(
    pillar_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Pillar).where(Pillar.id == pillar_id))
    pillar = result.scalar_one_or_none()
    if not pillar:
        raise HTTPException(status_code=404, detail="Pillar not found")

    await db.delete(pillar)
    await db.commit()
