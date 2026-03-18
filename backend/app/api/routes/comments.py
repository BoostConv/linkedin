"""API routes for comment management."""
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.post import Post
from app.models.comment import Comment
from app.api.routes.auth import get_current_user
from app.services.linkedin.comments import (
    fetch_post_comments,
    reply_to_comment,
    get_commenter_profile,
)
from app.services.ai.comment_replies import suggest_reply, batch_suggest_replies

router = APIRouter()

PROSPECT_KEYWORDS = [
    "founder", "fondateur", "ceo", "cmo", "coo", "co-founder",
    "head of marketing", "head of growth", "directeur marketing",
    "e-commerce", "ecommerce", "dtc", "d2c", "shopify",
]


class ReplyApproval(BaseModel):
    approved_reply: str


class ManualReply(BaseModel):
    reply_text: str


@router.get("/")
async def list_comments(
    status: str | None = None,
    post_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List comments with optional filtering."""
    query = select(Comment).order_by(desc(Comment.created_at))
    if status:
        query = query.where(Comment.reply_status == status)
    if post_id:
        query = query.where(Comment.post_id == post_id)

    result = await db.execute(query.limit(100))
    comments = result.scalars().all()

    return [
        {
            "id": str(c.id),
            "post_id": str(c.post_id),
            "author_name": c.author_name,
            "author_headline": c.author_headline,
            "content": c.content,
            "suggested_reply": c.suggested_reply,
            "approved_reply": c.approved_reply,
            "reply_status": c.reply_status,
            "is_prospect": c.is_prospect,
            "priority": c.priority,
            "commented_at": c.commented_at.isoformat() if c.commented_at else None,
            "replied_at": c.replied_at.isoformat() if c.replied_at else None,
        }
        for c in comments
    ]


@router.post("/fetch/{post_id}/")
async def fetch_comments(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch new comments from LinkedIn for a specific post."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post or not post.linkedin_post_id:
        raise HTTPException(status_code=404, detail="Post not found or not published on LinkedIn")

    if not current_user.linkedin_access_token:
        raise HTTPException(status_code=400, detail="LinkedIn not connected")

    raw_comments = await fetch_post_comments(
        access_token=current_user.linkedin_access_token,
        linkedin_post_id=post.linkedin_post_id,
    )

    new_count = 0
    for raw in raw_comments:
        # Skip if already imported
        existing = await db.execute(
            select(Comment).where(
                Comment.linkedin_comment_id == raw["linkedin_comment_id"]
            )
        )
        if existing.scalar_one_or_none():
            continue

        # Get commenter profile for prioritization
        profile = {"name": "", "headline": ""}
        if raw.get("author_linkedin_id"):
            profile = await get_commenter_profile(
                current_user.linkedin_access_token,
                raw["author_linkedin_id"],
            )

        # Detect prospects
        headline_lower = (profile.get("headline") or "").lower()
        is_prospect = any(kw in headline_lower for kw in PROSPECT_KEYWORDS)

        comment = Comment(
            post_id=post.id,
            linkedin_comment_id=raw["linkedin_comment_id"],
            author_name=profile.get("name") or "Inconnu",
            author_linkedin_id=raw.get("author_linkedin_id"),
            author_headline=profile.get("headline"),
            content=raw["content"],
            is_prospect=is_prospect,
            priority="high" if is_prospect else "normal",
            commented_at=(
                datetime.fromtimestamp(raw["commented_at"] / 1000, tz=timezone.utc)
                if raw.get("commented_at")
                else None
            ),
        )
        db.add(comment)
        new_count += 1

    await db.commit()
    return {"new_comments": new_count, "total_raw": len(raw_comments)}


@router.post("/suggest/{comment_id}/")
async def suggest_comment_reply(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Generate an AI reply suggestion for a single comment."""
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Get post content for context
    post_result = await db.execute(select(Post).where(Post.id == comment.post_id))
    post = post_result.scalar_one_or_none()

    reply = await suggest_reply(
        post_content=post.content if post else "",
        comment_text=comment.content,
        commenter_name=comment.author_name,
        commenter_headline=comment.author_headline,
        is_prospect=comment.is_prospect,
    )

    comment.suggested_reply = reply
    comment.reply_status = "suggested"
    await db.commit()
    await db.refresh(comment)

    return {"suggested_reply": reply}


@router.post("/suggest-batch/{post_id}/")
async def suggest_batch_replies(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Generate AI reply suggestions for all pending comments on a post."""
    result = await db.execute(
        select(Comment).where(
            Comment.post_id == post_id,
            Comment.reply_status == "pending",
        )
    )
    comments = list(result.scalars().all())

    if not comments:
        return {"suggested": 0}

    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one_or_none()

    comment_data = [
        {
            "id": str(c.id),
            "content": c.content,
            "author_name": c.author_name,
            "author_headline": c.author_headline,
            "is_prospect": c.is_prospect,
        }
        for c in comments
    ]

    suggestions = await batch_suggest_replies(
        post_content=post.content if post else "",
        comments=comment_data,
    )

    suggestion_map = {s["comment_id"]: s["suggested_reply"] for s in suggestions}

    for c in comments:
        if str(c.id) in suggestion_map:
            c.suggested_reply = suggestion_map[str(c.id)]
            c.reply_status = "suggested"

    await db.commit()
    return {"suggested": len(suggestion_map)}


@router.post("/approve/{comment_id}/")
async def approve_reply(
    comment_id: UUID,
    data: ReplyApproval,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Approve (and optionally edit) a reply before sending."""
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    comment.approved_reply = data.approved_reply
    comment.reply_status = "approved"
    await db.commit()

    return {"status": "approved"}


@router.post("/send/{comment_id}/")
async def send_reply(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send the approved reply to LinkedIn."""
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if not comment.approved_reply:
        raise HTTPException(status_code=400, detail="No approved reply")

    if not current_user.linkedin_access_token or not current_user.linkedin_person_id:
        raise HTTPException(status_code=400, detail="LinkedIn not connected")

    # Get post for LinkedIn ID
    post_result = await db.execute(select(Post).where(Post.id == comment.post_id))
    post = post_result.scalar_one_or_none()
    if not post or not post.linkedin_post_id:
        raise HTTPException(status_code=400, detail="Post not published on LinkedIn")

    reply_result = await reply_to_comment(
        access_token=current_user.linkedin_access_token,
        linkedin_post_id=post.linkedin_post_id,
        linkedin_comment_id=comment.linkedin_comment_id,
        person_id=current_user.linkedin_person_id,
        reply_text=comment.approved_reply,
    )

    comment.linkedin_reply_id = reply_result.get("linkedin_reply_id")
    comment.reply_status = "sent"
    comment.replied_at = datetime.now(timezone.utc)
    await db.commit()

    return {"status": "sent", "linkedin_reply_id": comment.linkedin_reply_id}


@router.post("/skip/{comment_id}/")
async def skip_comment(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Mark a comment as skipped (no reply needed)."""
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    comment.reply_status = "skipped"
    await db.commit()
    return {"status": "skipped"}
