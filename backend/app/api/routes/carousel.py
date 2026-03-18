"""API routes for carousel generation and preview."""
import base64
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.post import Post
from app.models.user import User
from app.api.routes.auth import get_current_user
from app.services.ai.carousel_writer import generate_carousel_content
from app.services.visual.carousel import (
    CarouselSlide,
    BrandConfig,
    generate_carousel_pdf,
)

router = APIRouter()


class CarouselGenerateRequest(BaseModel):
    topic: str
    pillar_name: str
    num_slides: int = 8


class CarouselSlideEdit(BaseModel):
    slide_type: str
    title: str = ""
    body: str = ""
    stat_number: str = ""
    stat_label: str = ""
    subtitle: str = ""


class CarouselPDFRequest(BaseModel):
    slides: list[CarouselSlideEdit]
    save_as_draft: bool = False
    pillar_id: UUID | None = None
    template_id: UUID | None = None


class CarouselSlideResponse(BaseModel):
    slide_type: str
    title: str = ""
    body: str = ""
    stat_number: str = ""
    stat_label: str = ""
    subtitle: str = ""


class CarouselGenerateResponse(BaseModel):
    slides: list[CarouselSlideResponse]


class CarouselPDFResponse(BaseModel):
    pdf_base64: str
    post_id: str | None = None


@router.post("/generate-slides/", response_model=CarouselGenerateResponse)
async def generate_slides(
    data: CarouselGenerateRequest,
    _: User = Depends(get_current_user),
):
    """Generate carousel slide content using AI."""
    try:
        slides = await generate_carousel_content(
            topic=data.topic,
            pillar_name=data.pillar_name,
            num_slides=data.num_slides,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Slide generation failed: {str(e)}")

    return CarouselGenerateResponse(
        slides=[CarouselSlideResponse(**s) for s in slides]
    )


@router.post("/generate-pdf/", response_model=CarouselPDFResponse)
async def generate_pdf(
    data: CarouselPDFRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a branded PDF from edited slides. Optionally save as draft post."""
    slides = [
        CarouselSlide(
            slide_type=s.slide_type,
            title=s.title,
            body=s.body,
            stat_number=s.stat_number,
            stat_label=s.stat_label,
            subtitle=s.subtitle,
        )
        for s in data.slides
    ]

    try:
        pdf_bytes = generate_carousel_pdf(slides, BrandConfig())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    post_id = None
    if data.save_as_draft:
        # Build content summary from slides for the post record
        content_parts = []
        for s in data.slides:
            if s.title:
                content_parts.append(s.title)
            if s.body:
                content_parts.append(s.body)
        content = "\n\n".join(content_parts)

        post = Post(
            user_id=current_user.id,
            content=content,
            hook=data.slides[0].title if data.slides else None,
            format="carousel",
            pillar_id=data.pillar_id,
            template_id=data.template_id,
            word_count=len(content.split()),
            status="draft",
            generation_metadata={"slides": [s.model_dump() for s in data.slides]},
        )
        db.add(post)
        await db.commit()
        await db.refresh(post)
        post_id = str(post.id)

    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    return CarouselPDFResponse(pdf_base64=pdf_b64, post_id=post_id)


@router.post("/preview-pdf/")
async def preview_pdf(
    data: CarouselPDFRequest,
    _: User = Depends(get_current_user),
):
    """Generate a PDF preview and return it directly as a file."""
    slides = [
        CarouselSlide(
            slide_type=s.slide_type,
            title=s.title,
            body=s.body,
            stat_number=s.stat_number,
            stat_label=s.stat_label,
            subtitle=s.subtitle,
        )
        for s in data.slides
    ]

    try:
        pdf_bytes = generate_carousel_pdf(slides, BrandConfig())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=carousel-preview.pdf"},
    )
