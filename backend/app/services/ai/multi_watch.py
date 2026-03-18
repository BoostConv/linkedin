"""Multi-source watch service — automated content monitoring.

Searches Google, YouTube, Twitter, and LinkedIn for CRO/conversion trends
and generates LinkedIn post ideas from the findings.
Designed to run automatically via cron (2x/week).
"""
import json
import random
import logging
import httpx
import anthropic
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.models.pillar import Pillar
from app.models.template import PostTemplate
from app.models.idea import Idea
from app.api.routes.auth import DEFAULT_USER_ID

settings = get_settings()
logger = logging.getLogger(__name__)

# ─── Search queries by topic ────────────────────────────────
WATCH_QUERIES = {
    "cro": [
        "conversion rate optimization e-commerce 2026",
        "CRO agency results case study",
        "taux de conversion e-commerce optimisation",
        "CRO audit e-commerce résultats",
        "conversion rate benchmarks by industry 2026",
    ],
    "post_click": [
        "post-click optimization advertising ROI",
        "ad spend wasted poor landing pages statistics",
        "expérience post-clic optimisation publicité",
        "message match advertising landing page",
        "post-click experience e-commerce ads",
    ],
    "landing_pages": [
        "landing page optimization best practices 2026",
        "landing page vs product page conversion rate",
        "landing page design e-commerce conversion",
        "landing page AB test case study results",
        "high converting landing page examples",
    ],
    "ab_testing": [
        "A/B testing e-commerce results case study",
        "AB test landing page conversion improvement",
        "test AB e-commerce résultats significatifs",
        "split testing best practices e-commerce",
        "A/B testing mistakes e-commerce brands",
    ],
    "ia_ecommerce": [
        "AI e-commerce conversion optimization",
        "intelligence artificielle e-commerce 2026",
        "AI generated ads creative testing performance",
        "IA personnalisation e-commerce conversion",
        "AI landing page optimization tools",
        "static ads AI e-commerce performance",
    ],
}


# ─── Google / Web search ────────────────────────────────────
async def search_google(query: str, num_results: int = 5) -> list[dict]:
    """Search via DuckDuckGo (no API key needed) or Brave if configured."""
    from app.services.ai.web_research import search_web
    return await search_web(query, num_results)


# ─── YouTube search ─────────────────────────────────────────
async def search_youtube(query: str, num_results: int = 5) -> list[dict]:
    """Search YouTube Data API v3 for relevant videos."""
    if not settings.youtube_api_key:
        logger.warning("YouTube API key not configured, skipping YouTube search")
        return []

    results = []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "key": settings.youtube_api_key,
                    "q": query,
                    "part": "snippet",
                    "type": "video",
                    "maxResults": num_results,
                    "order": "relevance",
                    "relevanceLanguage": "fr",
                    "publishedAfter": "2025-01-01T00:00:00Z",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("items", []):
                    snippet = item.get("snippet", {})
                    video_id = item.get("id", {}).get("videoId", "")
                    results.append({
                        "title": snippet.get("title", ""),
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "snippet": snippet.get("description", "")[:300],
                        "channel": snippet.get("channelTitle", ""),
                        "published": snippet.get("publishedAt", ""),
                        "source": "youtube",
                    })
            else:
                logger.error(f"YouTube API error: {resp.status_code} - {resp.text[:200]}")
    except Exception as e:
        logger.error(f"YouTube search error: {e}")

    return results


# ─── Twitter/X search via Apify ──────────────────────────────
async def search_twitter(query: str, num_results: int = 10) -> list[dict]:
    """Search Twitter/X via Apify Twitter Scraper actor."""
    if not settings.apify_api_token:
        logger.warning("Apify token not configured, skipping Twitter search")
        return []

    results = []
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            # Run Apify Twitter Scraper
            resp = await client.post(
                "https://api.apify.com/v2/acts/apidojo~tweet-scraper/run-sync-get-dataset-items",
                params={"token": settings.apify_api_token},
                json={
                    "searchTerms": [query],
                    "maxTweets": num_results,
                    "sort": "Top",
                    "tweetLanguage": "fr",
                },
                timeout=60,
            )
            if resp.status_code == 200:
                tweets = resp.json()
                for tweet in tweets[:num_results]:
                    results.append({
                        "title": f"@{tweet.get('author', {}).get('userName', 'unknown')}",
                        "url": tweet.get("url", ""),
                        "snippet": tweet.get("text", "")[:500],
                        "author": tweet.get("author", {}).get("name", ""),
                        "likes": tweet.get("likeCount", 0),
                        "retweets": tweet.get("retweetCount", 0),
                        "source": "twitter",
                    })
            else:
                logger.error(f"Apify Twitter error: {resp.status_code}")
    except Exception as e:
        logger.error(f"Twitter search error: {e}")

    return results


# ─── LinkedIn search via Apify ───────────────────────────────
async def search_linkedin_posts(query: str, num_results: int = 10) -> list[dict]:
    """Search LinkedIn posts via Apify LinkedIn Post Search Scraper."""
    if not settings.apify_api_token:
        logger.warning("Apify token not configured, skipping LinkedIn search")
        return []

    results = []
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.apify.com/v2/acts/curious_coder~linkedin-post-search-scraper/run-sync-get-dataset-items",
                params={"token": settings.apify_api_token},
                json={
                    "searchUrls": [f"https://www.linkedin.com/search/results/content/?keywords={query}"],
                    "maxResults": num_results,
                },
                timeout=60,
            )
            if resp.status_code == 200:
                posts = resp.json()
                for post in posts[:num_results]:
                    results.append({
                        "title": post.get("authorName", "Unknown"),
                        "url": post.get("postUrl", ""),
                        "snippet": (post.get("text", "") or "")[:500],
                        "author": post.get("authorName", ""),
                        "likes": post.get("numLikes", 0),
                        "comments": post.get("numComments", 0),
                        "source": "linkedin",
                    })
            else:
                logger.error(f"Apify LinkedIn error: {resp.status_code}")
    except Exception as e:
        logger.error(f"LinkedIn search error: {e}")

    return results


# ─── Main watch function ─────────────────────────────────────
async def run_multi_watch(
    db: AsyncSession,
    sources: list[str] | None = None,
    queries_per_source: int = 2,
    save: bool = True,
) -> dict:
    """Run automated multi-source watch and generate ideas.

    Args:
        db: Database session
        sources: List of sources to search ("google", "youtube", "twitter", "linkedin")
        queries_per_source: Number of search queries per source
        save: Whether to save generated ideas to DB

    Returns:
        Dict with generated ideas count and details
    """
    if sources is None:
        sources = ["google", "youtube", "twitter", "linkedin"]

    # Pick random queries
    all_queries = []
    for topic_queries in WATCH_QUERIES.values():
        all_queries.extend(topic_queries)

    selected_queries = random.sample(all_queries, min(queries_per_source * len(sources), len(all_queries)))

    # Run searches across all sources
    all_results = []
    query_idx = 0

    for source in sources:
        source_queries = selected_queries[query_idx:query_idx + queries_per_source]
        query_idx += queries_per_source

        for query in source_queries:
            try:
                if source == "google":
                    results = await search_google(query, num_results=5)
                    for r in results:
                        r["source"] = "google"
                elif source == "youtube":
                    results = await search_youtube(query, num_results=3)
                elif source == "twitter":
                    results = await search_twitter(query, num_results=5)
                elif source == "linkedin":
                    results = await search_linkedin_posts(query, num_results=5)
                else:
                    continue

                if results:
                    all_results.append({
                        "source": source,
                        "query": query,
                        "results": results,
                    })
            except Exception as e:
                logger.error(f"Error searching {source} for '{query}': {e}")

    if not all_results:
        return {"ideas": [], "generated": 0, "saved": 0, "sources_searched": sources}

    # Load pillars & templates
    pillars_result = await db.execute(
        select(Pillar).where(Pillar.is_active.is_(True)).order_by(Pillar.display_order)
    )
    pillars = list(pillars_result.scalars().all())

    templates_result = await db.execute(
        select(PostTemplate).where(PostTemplate.is_active.is_(True)).order_by(PostTemplate.display_order)
    )
    templates = list(templates_result.scalars().all())

    pillar_list = "\n".join(f"- {p.name}: {p.description}" for p in pillars)
    template_list = "\n".join(f"- {t.name}: {t.when_to_use}" for t in templates)

    # Format all results for Claude
    search_context = ""
    for r in all_results:
        source_emoji = {"google": "🌐", "youtube": "📺", "twitter": "🐦", "linkedin": "💼"}.get(r["source"], "🔍")
        search_context += f"\n\n### {source_emoji} {r['source'].upper()} — \"{r['query']}\"\n"
        for item in r["results"]:
            engagement = ""
            if item.get("likes"):
                engagement += f" | {item['likes']} likes"
            if item.get("comments"):
                engagement += f" | {item['comments']} comments"
            if item.get("channel"):
                engagement += f" | Chaîne: {item['channel']}"
            search_context += f"- **{item['title']}** ({item.get('url', '')}){engagement}\n  {item.get('snippet', '')[:200]}\n"

    total_ideas = max(8, len(all_results) * 2)

    prompt = f"""Tu es l'assistant éditorial de Sébastien Tortu, fondateur de Boost Conversion (agence CRO/post-clic pour marques e-commerce DTC 5-50M€).

OBJECTIF : Analyser cette veille multi-sources (Google, YouTube, Twitter, LinkedIn) pour identifier des sujets de posts LinkedIn percutants qui convainquent les e-commerçants d'investir dans le post-clic.

=== RÉSULTATS DE VEILLE ===
{search_context}

=== PILIERS DE CONTENU ===
{pillar_list}

=== TEMPLATES VIRAUX ===
{template_list}

Génère {total_ideas} idées de posts LinkedIn à partir de cette veille.

CONSIGNES :
- Chaque idée doit citer la SOURCE (quel article/vidéo/tweet l'a inspirée)
- Cherche les stats choquantes, les opinions clivantes, les tendances émergentes
- L'angle doit TOUJOURS ramener à "pourquoi il faut optimiser le post-clic"
- Varie les piliers et templates
- Indique la source originale (google/youtube/twitter/linkedin)

=== SCORING STRICT ===
- "high" : MAX 2 idées. Données chiffrées vérifiables + angle clivant
- "medium" : 3-4 idées. Tendance notable, bon potentiel
- "low" : le reste. Sujet utile mais plus générique

Réponds UNIQUEMENT en JSON :
[
  {{
    "title": "Titre court (max 10 mots)",
    "description": "Description de l'angle (3-4 phrases). Cite les stats/faits.",
    "pillar_name": "Nom du pilier",
    "template_name": "Nom du template",
    "priority": "high/medium/low",
    "tags": ["tag1", "tag2", "veille-auto"],
    "source_urls": ["url1"],
    "source_type": "google/youtube/twitter/linkedin",
    "research_insight": "Le fait/stat clé (1 phrase)"
  }}
]"""

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    # Parse JSON
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
        response_text = response_text.strip()

    ideas = json.loads(response_text)

    # Match pillar/template names
    pillar_map = {p.name.lower(): p for p in pillars}
    template_map = {t.name.lower(): t for t in templates}

    enriched = []
    saved_count = 0

    for idea in ideas:
        pillar_name = idea.get("pillar_name", "")
        template_name = idea.get("template_name", "")

        pillar = pillar_map.get(pillar_name.lower())
        if not pillar:
            for key, p in pillar_map.items():
                if pillar_name.lower() in key or key in pillar_name.lower():
                    pillar = p
                    break
            if not pillar and pillars:
                pillar = pillars[0]

        template = template_map.get(template_name.lower())
        if not template:
            for key, t in template_map.items():
                if template_name.lower() in key or key in template_name.lower():
                    template = t
                    break
            if not template and templates:
                template = templates[0]

        source_type = idea.get("source_type", "google")
        tags = idea.get("tags", [])
        if "veille-auto" not in tags:
            tags.append("veille-auto")
        tags.append(source_type)

        idea_data = {
            "title": idea.get("title", ""),
            "description": idea.get("description", ""),
            "pillar_name": pillar.name if pillar else "",
            "template_name": template.name if template else "",
            "priority": idea.get("priority", "medium"),
            "tags": tags,
            "source_urls": idea.get("source_urls", []),
            "source_type": source_type,
            "research_insight": idea.get("research_insight", ""),
        }
        enriched.append(idea_data)

        # Save to DB
        if save:
            raw_input = f"{idea_data['title']}\n\n{idea_data['description']}"
            if idea_data.get("research_insight"):
                raw_input += f"\n\nInsight: {idea_data['research_insight']}"

            db_idea = Idea(
                user_id=DEFAULT_USER_ID,
                input_type="raw_idea",
                raw_input=raw_input,
                source_url=idea_data["source_urls"][0] if idea_data["source_urls"] else None,
                suggested_pillar_id=pillar.id if pillar else None,
                suggested_template_id=template.id if template else None,
                suggested_angle=idea_data.get("research_insight", ""),
                priority=idea_data["priority"],
                tags=tags,
                status="new",
            )
            db.add(db_idea)
            saved_count += 1

    if save:
        await db.commit()

    return {
        "ideas": enriched,
        "generated": len(enriched),
        "saved": saved_count,
        "sources_searched": sources,
        "queries_run": len(all_results),
    }
