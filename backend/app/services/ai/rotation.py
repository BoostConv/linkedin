"""Pillar rotation algorithm.

Uses a weighted deficit algorithm on a 14-day sliding window
to ensure balanced content across all pillars.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pillar import Pillar
from app.models.post import Post


async def get_next_pillar(db: AsyncSession, user_id: UUID) -> Pillar:
    """Select the next pillar to publish based on weighted deficit.

    Algorithm:
    1. Calculate target ratio per pillar (weight / total weight)
    2. Compare with actual publications in last 14 days
    3. Select pillar with the highest deficit
    4. Tie-break: pillar not published for the longest time
    """
    # Get active pillars
    result = await db.execute(
        select(Pillar).where(Pillar.is_active.is_(True)).order_by(Pillar.display_order)
    )
    pillars = list(result.scalars().all())

    if not pillars:
        raise ValueError("No active pillars configured")

    total_weight = sum(p.weight for p in pillars)

    # Get published posts in last 14 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    posts_result = await db.execute(
        select(Post.pillar_id, func.count(Post.id))
        .where(
            Post.user_id == user_id,
            Post.status.in_(["published", "scheduled", "approved"]),
            Post.created_at >= cutoff,
        )
        .group_by(Post.pillar_id)
    )
    post_counts = dict(posts_result.all())

    total_posts = sum(post_counts.values()) or 1  # Avoid division by zero

    # Calculate deficit for each pillar
    deficits = []
    for pillar in pillars:
        target_ratio = pillar.weight / total_weight
        actual_count = post_counts.get(pillar.id, 0)
        actual_ratio = actual_count / total_posts

        deficit = target_ratio - actual_ratio
        deficits.append((pillar, deficit, actual_count))

    # Sort by deficit (highest first), then by least recent publication
    deficits.sort(key=lambda x: (-x[1], x[2]))

    return deficits[0][0]


async def get_pillar_balance(db: AsyncSession, user_id: UUID) -> list[dict]:
    """Get the current balance of pillars for the dashboard.

    Returns a list of dicts with pillar info, target %, actual %, and deficit.
    """
    result = await db.execute(
        select(Pillar).where(Pillar.is_active.is_(True)).order_by(Pillar.display_order)
    )
    pillars = list(result.scalars().all())
    total_weight = sum(p.weight for p in pillars) or 1

    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    posts_result = await db.execute(
        select(Post.pillar_id, func.count(Post.id))
        .where(
            Post.user_id == user_id,
            Post.status.in_(["published", "scheduled", "approved"]),
            Post.created_at >= cutoff,
        )
        .group_by(Post.pillar_id)
    )
    post_counts = dict(posts_result.all())
    total_posts = sum(post_counts.values()) or 1

    balance = []
    for pillar in pillars:
        target = pillar.weight / total_weight
        actual_count = post_counts.get(pillar.id, 0)
        actual = actual_count / total_posts

        balance.append({
            "pillar_id": str(pillar.id),
            "pillar_name": pillar.name,
            "weight": pillar.weight,
            "target_pct": round(target * 100, 1),
            "actual_pct": round(actual * 100, 1),
            "deficit_pct": round((target - actual) * 100, 1),
            "post_count_14d": actual_count,
        })

    return balance
