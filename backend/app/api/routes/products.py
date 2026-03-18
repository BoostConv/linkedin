"""CRUD endpoints for Products/Services (Benchmark GA4, NeuroCRO Score, etc.)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.product import Product
from app.models.user import User
from app.api.routes.auth import get_current_user

router = APIRouter()


class ProductCreate(BaseModel):
    name: str
    slug: str
    tagline: str
    description: str
    target_audience: str
    key_benefits: list[str] = []
    pain_points: list[str] = []
    proof_points: list[str] | None = None
    cta_text: str | None = None
    price_info: str | None = None
    url: str | None = None
    display_order: int = 0
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    tagline: str | None = None
    description: str | None = None
    target_audience: str | None = None
    key_benefits: list[str] | None = None
    pain_points: list[str] | None = None
    proof_points: list[str] | None = None
    cta_text: str | None = None
    price_info: str | None = None
    url: str | None = None
    display_order: int | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: str
    name: str
    slug: str
    tagline: str
    description: str
    target_audience: str
    key_benefits: list[str]
    pain_points: list[str]
    proof_points: list[str] | None
    cta_text: str | None
    price_info: str | None
    url: str | None
    display_order: int
    is_active: bool


@router.get("/", response_model=list[ProductResponse])
async def list_products(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Product).order_by(Product.display_order)
    )
    products = result.scalars().all()
    return [
        ProductResponse(
            id=str(p.id),
            name=p.name,
            slug=p.slug,
            tagline=p.tagline,
            description=p.description,
            target_audience=p.target_audience,
            key_benefits=p.key_benefits or [],
            pain_points=p.pain_points or [],
            proof_points=p.proof_points,
            cta_text=p.cta_text,
            price_info=p.price_info,
            url=p.url,
            display_order=p.display_order,
            is_active=p.is_active,
        )
        for p in products
    ]


@router.post("/", response_model=ProductResponse)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    product = Product(
        name=data.name,
        slug=data.slug,
        tagline=data.tagline,
        description=data.description,
        target_audience=data.target_audience,
        key_benefits=data.key_benefits,
        pain_points=data.pain_points,
        proof_points=data.proof_points,
        cta_text=data.cta_text,
        price_info=data.price_info,
        url=data.url,
        display_order=data.display_order,
        is_active=data.is_active,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return ProductResponse(
        id=str(product.id),
        name=product.name,
        slug=product.slug,
        tagline=product.tagline,
        description=product.description,
        target_audience=product.target_audience,
        key_benefits=product.key_benefits or [],
        pain_points=product.pain_points or [],
        proof_points=product.proof_points,
        cta_text=product.cta_text,
        price_info=product.price_info,
        url=product.url,
        display_order=product.display_order,
        is_active=product.is_active,
    )


@router.patch("/{product_id}/", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    await db.commit()
    await db.refresh(product)
    return ProductResponse(
        id=str(product.id),
        name=product.name,
        slug=product.slug,
        tagline=product.tagline,
        description=product.description,
        target_audience=product.target_audience,
        key_benefits=product.key_benefits or [],
        pain_points=product.pain_points or [],
        proof_points=product.proof_points,
        cta_text=product.cta_text,
        price_info=product.price_info,
        url=product.url,
        display_order=product.display_order,
        is_active=product.is_active,
    )


@router.delete("/{product_id}/")
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.delete(product)
    await db.commit()
    return {"status": "deleted"}
