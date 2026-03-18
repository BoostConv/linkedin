from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.post import Post
from app.models.user import User
from app.api.routes.auth import get_current_user
from app.services.ai.generator import generate_post, generate_post_variants
from app.services.ai.validator import validate_post
from app.services.ai.rotation import get_next_pillar, get_pillar_balance
from app.services.ai.case_study import generate_case_study
from app.services.ai.auto_select import auto_select_pillar_and_template
from app.services.ai.visual_suggest import suggest_visual_for_post

router = APIRouter()


class GenerateRequest(BaseModel):
    pillar_id: UUID
    template_id: UUID
    topic: str | None = None
    additional_context: str | None = None
    save_as_draft: bool = True


class GenerateVariantsRequest(BaseModel):
    pillar_id: UUID
    template_id: UUID
    topic: str | None = None
    count: int = 2


class ValidateRequest(BaseModel):
    content: str


class ValidationResult(BaseModel):
    score: int
    issues: list[dict]
    passed: bool
    error_count: int
    warning_count: int


class GeneratedPost(BaseModel):
    content: str
    hook: str | None = None
    validation: ValidationResult
    post_id: UUID | None = None  # If saved as draft


@router.post("/generate/", response_model=GeneratedPost)
async def generate(
    data: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await generate_post(
            db=db,
            pillar_id=data.pillar_id,
            template_id=data.template_id,
            topic=data.topic,
            additional_context=data.additional_context,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

    # Validate
    validation = validate_post(result["content"])

    post_id = None
    if data.save_as_draft:
        post = Post(
            user_id=current_user.id,
            content=result["content"],
            hook=result["hook"],
            format="text",
            pillar_id=data.pillar_id,
            template_id=data.template_id,
            word_count=len(result["content"].split()),
            generation_prompt=result["generation_prompt"],
            generation_metadata=result["generation_metadata"],
            anti_ai_score=validation["score"],
            anti_ai_issues=validation["issues"],
            status="draft",
        )
        db.add(post)
        await db.commit()
        await db.refresh(post)
        post_id = post.id

    return GeneratedPost(
        content=result["content"],
        hook=result["hook"],
        validation=ValidationResult(**validation),
        post_id=post_id,
    )


@router.post("/generate/variants/", response_model=list[GeneratedPost])
async def generate_variants(
    data: GenerateVariantsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        variants = await generate_post_variants(
            db=db,
            pillar_id=data.pillar_id,
            template_id=data.template_id,
            topic=data.topic,
            count=data.count,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

    results = []
    for variant in variants:
        validation = validate_post(variant["content"])
        results.append(
            GeneratedPost(
                content=variant["content"],
                hook=variant["hook"],
                validation=ValidationResult(**validation),
            )
        )

    return results


@router.post("/validate/", response_model=ValidationResult)
async def validate(
    data: ValidateRequest,
    _: User = Depends(get_current_user),
):
    return validate_post(data.content)


@router.get("/next-pillar/")
async def next_pillar(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the recommended next pillar based on weighted deficit algorithm."""
    try:
        pillar = await get_next_pillar(db, current_user.id)
        return {"pillar_id": str(pillar.id), "pillar_name": pillar.name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/pillar-balance/")
async def pillar_balance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current pillar balance for the dashboard."""
    return await get_pillar_balance(db, current_user.id)


class AutoGenerateRequest(BaseModel):
    """Just an idea/topic — the AI picks the best pillar + template."""
    topic: str
    source_url: str | None = None
    idea_id: UUID | None = None  # Link to an existing idea
    save_as_draft: bool = True


class AutoGenerateResponse(BaseModel):
    content: str
    hook: str | None = None
    validation: ValidationResult
    post_id: UUID | None = None
    pillar_name: str
    template_name: str
    suggested_angle: str
    reasoning: str


@router.post("/generate/auto/", response_model=AutoGenerateResponse)
async def generate_auto(
    data: AutoGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a post from just a topic — AI auto-selects pillar & template."""
    # Step 1: AI selects pillar + template
    try:
        selection = await auto_select_pillar_and_template(
            db=db,
            idea_text=data.topic,
            user_id=current_user.id,
            source_url=data.source_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-selection failed: {str(e)}")

    # Step 2: Generate the post with selected pillar + template
    try:
        result = await generate_post(
            db=db,
            pillar_id=UUID(selection["pillar_id"]),
            template_id=UUID(selection["template_id"]),
            topic=data.topic,
            additional_context=f"Angle suggéré: {selection['suggested_angle']}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

    # Step 3: Validate
    validation = validate_post(result["content"])

    # Step 4: Save as draft
    post_id = None
    if data.save_as_draft:
        post = Post(
            user_id=current_user.id,
            content=result["content"],
            hook=result["hook"],
            format="text",
            pillar_id=UUID(selection["pillar_id"]),
            template_id=UUID(selection["template_id"]),
            idea_id=data.idea_id,
            word_count=len(result["content"].split()),
            generation_prompt=result["generation_prompt"],
            generation_metadata={
                **result["generation_metadata"],
                "auto_selected": True,
                "selection_reasoning": selection["reasoning"],
            },
            anti_ai_score=validation["score"],
            anti_ai_issues=validation["issues"],
            status="draft",
        )
        db.add(post)
        await db.commit()
        await db.refresh(post)
        post_id = post.id

    # Step 5: Update the linked idea status if provided
    if data.idea_id:
        from app.models.idea import Idea
        idea_result = await db.execute(
            select(Idea).where(Idea.id == data.idea_id)
        )
        idea = idea_result.scalar_one_or_none()
        if idea:
            idea.status = "drafting"
            idea.suggested_pillar_id = UUID(selection["pillar_id"])
            idea.suggested_template_id = UUID(selection["template_id"])
            idea.suggested_angle = selection["suggested_angle"]
            await db.commit()

    return AutoGenerateResponse(
        content=result["content"],
        hook=result["hook"],
        validation=ValidationResult(**validation),
        post_id=post_id,
        pillar_name=selection.get("pillar_name", ""),
        template_name=selection.get("template_name", ""),
        suggested_angle=selection["suggested_angle"],
        reasoning=selection["reasoning"],
    )


class CaseStudyRequest(BaseModel):
    client_name: str
    industry: str
    problem: str
    actions: str
    results: str
    anonymize: bool = True
    additional_context: str | None = None
    save_as_draft: bool = True


@router.post("/generate/case-study/")
async def generate_case_study_endpoint(
    data: CaseStudyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a structured case study post."""
    try:
        result = await generate_case_study(
            client_name=data.client_name,
            industry=data.industry,
            problem=data.problem,
            actions=data.actions,
            results=data.results,
            anonymize=data.anonymize,
            additional_context=data.additional_context,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Case study generation failed: {str(e)}")

    validation = validate_post(result["content"])

    post_id = None
    if data.save_as_draft:
        post = Post(
            user_id=current_user.id,
            content=result["content"],
            hook=result.get("hook"),
            format=result.get("suggested_format", "text"),
            word_count=len(result["content"].split()),
            anti_ai_score=validation["score"],
            anti_ai_issues=validation["issues"],
            generation_metadata={
                "type": "case_study",
                "carousel_slides": result.get("carousel_slides"),
            },
            status="draft",
        )
        db.add(post)
        await db.commit()
        await db.refresh(post)
        post_id = str(post.id)

    return {
        "content": result["content"],
        "hook": result.get("hook"),
        "suggested_format": result.get("suggested_format"),
        "carousel_slides": result.get("carousel_slides"),
        "validation": validation,
        "post_id": post_id,
    }


class VisualSuggestionRequest(BaseModel):
    content: str
    pillar_name: str = ""


class CarouselSlideIdea(BaseModel):
    slide_number: int
    title: str
    content: str
    visual_note: str = ""


class VisualSuggestionResponse(BaseModel):
    visual_type: str  # "carousel", "image", "text_only"
    reasoning: str
    visual_description: str
    carousel_slides: list[CarouselSlideIdea] | None = None


@router.post("/suggest-visual/", response_model=VisualSuggestionResponse)
async def suggest_visual(
    data: VisualSuggestionRequest,
    _: User = Depends(get_current_user),
):
    """Suggest the best visual format for a post."""
    try:
        result = await suggest_visual_for_post(
            content=data.content,
            pillar_name=data.pillar_name,
        )
        return VisualSuggestionResponse(
            visual_type=result.get("visual_type", "text_only"),
            reasoning=result.get("reasoning", ""),
            visual_description=result.get("visual_description", ""),
            carousel_slides=[
                CarouselSlideIdea(**s) for s in (result.get("carousel_slides") or [])
            ] if result.get("carousel_slides") else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Visual suggestion failed: {str(e)}")
