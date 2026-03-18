"""Analyze competitor posts to extract topics, trends, and relevance."""
import json

from app.config import get_settings
from app.services.ai.openai_helper import openai_complete

settings = get_settings()


async def analyze_competitor_posts(posts: list[dict], pillar_names: list[str]) -> list[dict]:
    """Analyze a batch of competitor posts using Claude.

    Extracts topic, detected template, and relevance to our pillars.

    Args:
        posts: List of dicts with 'content', 'likes', 'comments'.
        pillar_names: List of pillar names for relevance scoring.

    Returns:
        List of analysis dicts for each post.
    """
    if not posts:
        return []

    # Build posts summary for the prompt
    posts_text = ""
    for i, p in enumerate(posts[:15]):  # Max 15 to stay within token limits
        content_preview = (p.get("content", "") or "")[:300]
        posts_text += (
            f"\n--- Post {i + 1} ---\n"
            f"Contenu: {content_preview}\n"
            f"Likes: {p.get('likes', 0)} | Commentaires: {p.get('comments', 0)} | Partages: {p.get('shares', 0)}\n"
        )

    pillars_str = ", ".join(pillar_names)

    prompt = f"""Analyse ces posts LinkedIn de concurrents et extrais des insights.

Nos piliers de contenu : {pillars_str}

{posts_text}

Pour chaque post, réponds en JSON array avec :
- "index": numéro du post (1-based)
- "detected_topic": sujet principal (max 50 chars)
- "detected_template": type de post ("histoire", "data", "opinion", "curation", "étude_de_cas", "actu", "autre")
- "relevance_score": pertinence pour nos piliers (0.0 à 1.0)
- "relevant_pillar": le pilier le plus proche parmi nos piliers (ou null)
- "key_insight": ce qu'on peut en retenir (1 phrase)
- "engagement_quality": "high" si le ratio engagement/contenu est bon, "medium", "low"

Réponds UNIQUEMENT avec le JSON array."""

    response_text = openai_complete(
        system="Tu es un analyste de contenu LinkedIn. Réponds uniquement en JSON.",
        user=prompt,
        max_tokens=2000,
    )

    # Handle markdown wrapping
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
        response_text = response_text.strip()

    return json.loads(response_text)


async def detect_trends(analyses: list[dict]) -> list[dict]:
    """Detect trending topics from analyzed competitor posts.

    Groups posts by topic and calculates trend signals.
    """
    topic_groups = {}
    for a in analyses:
        topic = a.get("detected_topic", "").lower().strip()
        if not topic:
            continue
        if topic not in topic_groups:
            topic_groups[topic] = {"count": 0, "total_relevance": 0, "high_engagement": 0}
        topic_groups[topic]["count"] += 1
        topic_groups[topic]["total_relevance"] += a.get("relevance_score", 0)
        if a.get("engagement_quality") == "high":
            topic_groups[topic]["high_engagement"] += 1

    trends = []
    for topic, data in topic_groups.items():
        if data["count"] >= 2:
            trends.append({
                "topic": topic,
                "frequency": data["count"],
                "avg_relevance": round(data["total_relevance"] / data["count"], 2),
                "high_engagement_ratio": round(data["high_engagement"] / data["count"], 2),
                "trend_score": round(
                    data["count"] * 0.4 +
                    (data["total_relevance"] / data["count"]) * 0.4 +
                    (data["high_engagement"] / data["count"]) * 0.2,
                    2,
                ),
            })

    return sorted(trends, key=lambda x: x["trend_score"], reverse=True)
