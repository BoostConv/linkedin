from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.idea import Idea
from app.models.user import User
from app.api.routes.auth import get_current_user

router = APIRouter()


class IdeaCreate(BaseModel):
    input_type: str  # "url", "raw_idea", "repost", "theme_list"
    raw_input: str
    source_url: str | None = None


class IdeaUpdate(BaseModel):
    status: str | None = None
    priority: str | None = None
    suggested_angle: str | None = None


class IdeaResponse(BaseModel):
    id: UUID
    input_type: str
    raw_input: str
    source_url: str | None = None
    scraped_content: str | None = None
    suggested_pillar_id: UUID | None = None
    suggested_template_id: UUID | None = None
    suggested_angle: str | None = None
    priority: str
    tags: dict | None = None
    status: str

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[IdeaResponse])
async def list_ideas(
    status: str | None = None,
    priority: str | None = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Idea).where(Idea.user_id == current_user.id)
    if status:
        query = query.where(Idea.status == status)
    if priority:
        query = query.where(Idea.priority == priority)
    query = query.order_by(Idea.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=IdeaResponse, status_code=201)
async def create_idea(
    data: IdeaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    idea = Idea(
        user_id=current_user.id,
        input_type=data.input_type,
        raw_input=data.raw_input,
        source_url=data.source_url,
    )
    db.add(idea)
    await db.commit()
    await db.refresh(idea)

    # Trigger AI analysis in background (best-effort, don't block)
    try:
        from app.services.ai.idea_analyzer import analyze_idea
        await analyze_idea(db, idea.id)
        await db.refresh(idea)
    except Exception:
        pass  # Non-blocking: if analysis fails, the idea is still saved

    return idea


@router.get("/{idea_id}/", response_model=IdeaResponse)
async def get_idea(
    idea_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Idea).where(Idea.id == idea_id, Idea.user_id == current_user.id)
    )
    idea = result.scalar_one_or_none()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    return idea


@router.patch("/{idea_id}/", response_model=IdeaResponse)
async def update_idea(
    idea_id: UUID,
    data: IdeaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Idea).where(Idea.id == idea_id, Idea.user_id == current_user.id)
    )
    idea = result.scalar_one_or_none()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(idea, field, value)

    await db.commit()
    await db.refresh(idea)
    return idea


@router.post("/{idea_id}/analyze/", response_model=IdeaResponse)
async def analyze_idea_endpoint(
    idea_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-analyze an idea with AI to get pillar/template/angle suggestions."""
    result = await db.execute(
        select(Idea).where(Idea.id == idea_id, Idea.user_id == current_user.id)
    )
    idea = result.scalar_one_or_none()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    from app.services.ai.idea_analyzer import analyze_idea
    try:
        await analyze_idea(db, idea.id)
        await db.refresh(idea)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    return idea


class GenerateIdeasRequest(BaseModel):
    count: int = 10
    pillar_id: UUID | None = None
    save: bool = True


@router.post("/generate-bank/")
async def generate_idea_bank(
    data: GenerateIdeasRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a bank of post ideas using AI.

    Analyzes pillars, recent posts, and trends to suggest fresh topics.
    """
    from app.services.ai.idea_generator import generate_idea_bank as gen_bank, save_generated_ideas

    try:
        ideas = await gen_bank(
            db=db,
            count=data.count,
            focus_pillar_id=data.pillar_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Idea generation failed: {str(e)}")

    saved_count = 0
    if data.save:
        saved_count = await save_generated_ideas(db, ideas)

    return {
        "ideas": ideas,
        "generated": len(ideas),
        "saved": saved_count,
    }


# ─── Generate from brief ─────────────────────────────────────
class BriefRequest(BaseModel):
    """Generate multiple idea angles from a single brief."""
    brief: str
    count: int = 6
    channel: str = "linkedin"  # "linkedin", "newsletter", "both"
    save_selected: list[int] | None = None  # indices of ideas to save


@router.post("/generate-from-brief/")
async def generate_from_brief(
    data: BriefRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate multiple post idea variations from a single brief/topic.

    Returns several different angles so the user can pick the best ones.
    """
    from app.services.ai.brief_generator import generate_ideas_from_brief
    from app.services.ai.idea_generator import save_generated_ideas

    try:
        ideas = await generate_ideas_from_brief(
            db=db,
            brief=data.brief,
            count=data.count,
            channel=data.channel,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Brief generation failed: {str(e)}")

    saved_count = 0
    if data.save_selected is not None:
        to_save = [ideas[i] for i in data.save_selected if i < len(ideas)]
        saved_count = await save_generated_ideas(db, to_save)

    return {
        "ideas": ideas,
        "generated": len(ideas),
        "saved": saved_count,
    }


# ─── Web research veille ─────────────────────────────────────
class WebResearchRequest(BaseModel):
    """Search the web for trending CRO/conversion topics."""
    num_queries: int = 4
    ideas_count: int = 3  # ideas per query
    save: bool = True


@router.post("/web-research/")
async def web_research(
    data: WebResearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search the web for trending CRO/conversion topics and generate ideas.

    Finds fresh content about conversion optimization, landing pages, A/B testing,
    and generates LinkedIn post ideas based on the findings.
    """
    from app.services.ai.web_research import web_research_ideas
    from app.services.ai.idea_generator import save_generated_ideas

    try:
        ideas = await web_research_ideas(
            db=db,
            num_queries=data.num_queries,
            ideas_per_query=data.ideas_count,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Web research failed: {str(e)}")

    saved_count = 0
    if data.save:
        saved_count = await save_generated_ideas(db, ideas)

    return {
        "ideas": ideas,
        "generated": len(ideas),
        "saved": saved_count,
    }


@router.post("/reanalyze-all/")
@router.post("/reanalyze-all/")
async def reanalyze_all_ideas(
    batch_size: int = Query(default=8, le=20),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-analyze active ideas in batches to recalculate priorities.

    Use offset to paginate through all ideas (Vercel has 60s timeout).
    Call multiple times: offset=0, offset=8, offset=16, etc.
    """
    import logging
    logger = logging.getLogger(__name__)

    from app.services.ai.idea_analyzer import analyze_idea

    result = await db.execute(
        select(Idea)
        .where(Idea.user_id == current_user.id, Idea.status.in_(["new", "drafting", "planned"]))
        .order_by(Idea.created_at.desc())
    )
    all_ideas = list(result.scalars().all())
    total = len(all_ideas)
    batch = all_ideas[offset:offset + batch_size]

    analyzed = 0
    errors = 0
    results_summary = {"high": 0, "medium": 0, "low": 0}

    for idea in batch:
        try:
            analysis = await analyze_idea(db, idea.id)
            priority = analysis.get("priority", "medium")
            results_summary[priority] = results_summary.get(priority, 0) + 1
            analyzed += 1
            logger.info(f"Re-analyzed idea {idea.id}: priority={priority}")
        except Exception as e:
            errors += 1
            logger.error(f"Failed to re-analyze idea {idea.id}: {e}")

    next_offset = offset + batch_size
    has_more = next_offset < total

    return {
        "total": total,
        "batch_analyzed": analyzed,
        "batch_errors": errors,
        "distribution": results_summary,
        "offset": offset,
        "next_offset": next_offset if has_more else None,
        "has_more": has_more,
        "remaining": max(0, total - next_offset),
    }


@router.delete("/{idea_id}/", status_code=204)
async def delete_idea(
    idea_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Idea).where(Idea.id == idea_id, Idea.user_id == current_user.id)
    )
    idea = result.scalar_one_or_none()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    await db.delete(idea)
    await db.commit()
