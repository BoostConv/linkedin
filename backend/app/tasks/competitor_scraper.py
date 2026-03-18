"""Celery task for daily competitor post scraping and analysis."""
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

from app.tasks import celery_app
from app.config import get_settings
from app.models.competitor import Competitor, CompetitorPost
from app.models.pillar import Pillar

settings = get_settings()


async def _scrape_and_analyze(competitor_id: str, linkedin_url: str, pillar_names: list[str]):
    """Scrape posts for one competitor and analyze them."""
    from app.services.competitors.scraper import scrape_competitor_posts
    from app.services.competitors.analyzer import analyze_competitor_posts

    posts = await scrape_competitor_posts(linkedin_url, max_posts=10)
    if not posts:
        return 0

    analyses = await analyze_competitor_posts(posts, pillar_names)

    engine = create_engine(settings.database_url_sync)
    saved = 0
    with Session(engine) as db:
        for i, post_data in enumerate(posts):
            # Skip if we already scraped this URL
            if post_data.get("post_url"):
                existing = db.execute(
                    select(CompetitorPost).where(
                        CompetitorPost.linkedin_post_url == post_data["post_url"]
                    )
                ).scalar_one_or_none()
                if existing:
                    continue

            analysis = next((a for a in analyses if a.get("index") == i + 1), {})

            cp = CompetitorPost(
                competitor_id=competitor_id,
                linkedin_post_url=post_data.get("post_url"),
                content=post_data.get("content", ""),
                post_type=post_data.get("post_type"),
                likes=post_data.get("likes", 0),
                comments=post_data.get("comments", 0),
                shares=post_data.get("shares", 0),
                detected_topic=analysis.get("detected_topic"),
                detected_template=analysis.get("detected_template"),
                relevance_score=analysis.get("relevance_score"),
                analysis={
                    "relevant_pillar": analysis.get("relevant_pillar"),
                    "key_insight": analysis.get("key_insight"),
                    "engagement_quality": analysis.get("engagement_quality"),
                },
                posted_at=(
                    datetime.fromisoformat(post_data["posted_at"].replace("Z", "+00:00"))
                    if post_data.get("posted_at")
                    else None
                ),
            )
            db.add(cp)
            saved += 1

        db.commit()

    return saved


@celery_app.task(name="app.tasks.competitor_scraper.scrape_competitors")
def scrape_competitors():
    """Scrape posts for all active competitors."""
    engine = create_engine(settings.database_url_sync)

    with Session(engine) as db:
        competitors = db.execute(
            select(Competitor).where(Competitor.is_active.is_(True))
        ).scalars().all()

        pillars = db.execute(
            select(Pillar).where(Pillar.is_active.is_(True))
        ).scalars().all()
        pillar_names = [p.name for p in pillars]

    total_saved = 0
    for comp in competitors:
        try:
            saved = asyncio.run(
                _scrape_and_analyze(str(comp.id), comp.linkedin_url, pillar_names)
            )
            total_saved += saved
        except Exception as e:
            print(f"Error scraping {comp.name}: {e}")

    return f"Scraped {total_saved} new posts from {len(competitors)} competitors"
