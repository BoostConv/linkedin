"""Web research service — searches the web for trending CRO/conversion topics.

Finds fresh content about CRO, post-click optimization, landing pages, A/B testing,
e-commerce conversion, and generates LinkedIn post ideas from the findings.
"""
import json
import httpx
import anthropic
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.models.pillar import Pillar
from app.models.template import PostTemplate
from app.models.product import Product

settings = get_settings()

# Search queries rotated to cover different angles
RESEARCH_QUERIES = [
    "e-commerce conversion rate optimization 2026",
    "landing page optimization best practices",
    "post-click optimization advertising ROI",
    "A/B testing e-commerce results case study",
    "DTC brands conversion rate statistics",
    "quiz funnel e-commerce conversion",
    "ad spend wasted poor landing pages statistics",
    "CRO agency results e-commerce",
    "message match advertising landing page",
    "e-commerce post-click experience",
    "landing page vs product page conversion",
    "creative testing static ads AI 2026",
    "whitelisting UGC e-commerce performance",
    "Google Ads landing page quality score impact",
    "Meta ads post-click conversion drop",
    "e-commerce brands wasting ad spend",
    "conversion rate benchmarks by industry 2026",
    "personalization landing page revenue impact",
]


async def search_web(query: str, num_results: int = 5) -> list[dict]:
    """Search the web using a search API and return results.

    Uses Brave Search API if available, falls back to DuckDuckGo HTML scraping.
    """
    results = []

    # Try Brave Search API first (if key available)
    brave_key = getattr(settings, 'brave_api_key', None)
    if brave_key:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    headers={"X-Subscription-Token": brave_key, "Accept": "application/json"},
                    params={"q": query, "count": num_results, "lang": "fr"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for r in data.get("web", {}).get("results", [])[:num_results]:
                        results.append({
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "snippet": r.get("description", ""),
                        })
                    return results
        except Exception:
            pass

    # Fallback: DuckDuckGo lite (no API key needed)
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
            )
            if resp.status_code == 200:
                text = resp.text
                # Simple HTML parsing for DuckDuckGo results
                import re
                # Extract result blocks
                result_blocks = re.findall(
                    r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
                    text, re.DOTALL
                )
                for url, title, snippet in result_blocks[:num_results]:
                    # Clean HTML tags
                    title = re.sub(r'<[^>]+>', '', title).strip()
                    snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                    # DuckDuckGo wraps URLs
                    if 'uddg=' in url:
                        url_match = re.search(r'uddg=([^&]+)', url)
                        if url_match:
                            from urllib.parse import unquote
                            url = unquote(url_match.group(1))
                    results.append({"title": title, "url": url, "snippet": snippet})
    except Exception:
        pass

    return results


async def web_research_ideas(
    db: AsyncSession,
    num_queries: int = 4,
    ideas_per_query: int = 3,
) -> list[dict]:
    """Search the web for trending CRO/conversion topics and generate post ideas.

    Args:
        db: Database session
        num_queries: Number of search queries to run
        ideas_per_query: How many ideas to generate from each query's results

    Returns:
        List of idea dicts with: title, description, pillar_name, template_name,
        priority, tags, source_urls, research_context
    """
    import random

    # Pick random queries to diversify
    queries = random.sample(RESEARCH_QUERIES, min(num_queries, len(RESEARCH_QUERIES)))

    # Run searches
    all_results = []
    for query in queries:
        results = await search_web(query, num_results=5)
        all_results.append({"query": query, "results": results})

    if not any(r["results"] for r in all_results):
        raise ValueError("Aucun résultat de recherche trouvé. Vérifiez la connexion internet.")

    # Load pillars & templates for context
    pillars_result = await db.execute(
        select(Pillar).where(Pillar.is_active.is_(True)).order_by(Pillar.display_order)
    )
    pillars = list(pillars_result.scalars().all())

    templates_result = await db.execute(
        select(PostTemplate).where(PostTemplate.is_active.is_(True)).order_by(PostTemplate.display_order)
    )
    templates = list(templates_result.scalars().all())

    products_result = await db.execute(
        select(Product).where(Product.is_active.is_(True))
    )
    products = list(products_result.scalars().all())

    pillar_list = "\n".join(f"- {p.name}: {p.description}" for p in pillars)
    template_list = "\n".join(f"- {t.name}: {t.when_to_use}" for t in templates)
    products_list = "\n".join(
        f"- {p.name}: {p.tagline} | CTA: {p.cta_text or 'N/A'}"
        for p in products
    ) if products else "Aucun produit configuré."

    # Format search results for Claude
    search_context = ""
    for r in all_results:
        if r["results"]:
            search_context += f"\n\n### Recherche: \"{r['query']}\"\n"
            for item in r["results"]:
                search_context += f"- **{item['title']}** ({item['url']})\n  {item['snippet']}\n"

    total_ideas = num_queries * ideas_per_query

    prompt = f"""Tu es l'assistant éditorial de Sébastien Tortu, fondateur de Boost Conversion (agence CRO/post-clic pour marques e-commerce DTC 5-50M€).

OBJECTIF PRINCIPAL : Trouver des angles de posts LinkedIn qui convainquent les marques e-commerce qui investissent en ads de faire appel à Boost Conversion pour gérer leur post-clic (landing pages, A/B tests, quiz funnels, whitelisting, créa IA, etc.).

Voici les résultats de recherche web actuels sur des sujets liés au CRO et à l'optimisation post-clic :

{search_context}

=== PILIERS DE CONTENU ===
{pillar_list}

=== TEMPLATES VIRAUX ===
{template_list}

=== PRODUITS/SERVICES À PROMOUVOIR ===
{products_list}

À partir de ces résultats de recherche, génère {total_ideas} idées de posts LinkedIn PERCUTANTES.

CONSIGNES CRUCIALES :
- Chaque idée doit s'appuyer sur un fait, une stat, ou une tendance trouvée dans les résultats de recherche
- L'angle doit TOUJOURS ramener à pourquoi les marques ont besoin d'optimiser leur post-clic
- Cherche les stats choquantes (% d'ad spend gaspillé, taux de conversion moyens, etc.)
- Cherche les case studies et résultats concrets à transformer en posts
- Propose des opinions tranchées sur les tendances trouvées
- Au moins 2-3 idées doivent mentionner un produit/service Boost Conversion
- Priorité "high" pour les sujets avec des données chiffrées ou des tendances fortes

Réponds UNIQUEMENT en JSON :
[
  {{
    "title": "Titre court (max 10 mots)",
    "description": "Description détaillée de l'angle du post (3-4 phrases). Cite les stats/faits trouvés.",
    "pillar_name": "Nom du pilier",
    "template_name": "Nom du template suggéré",
    "priority": "high/medium/low",
    "tags": ["tag1", "tag2"],
    "source_urls": ["url1", "url2"],
    "research_insight": "Le fait/stat clé qui motive cette idée (1 phrase)"
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

    # Match pillar and template names to IDs
    pillar_map = {p.name.lower(): p for p in pillars}
    template_map = {t.name.lower(): t for t in templates}

    enriched = []
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

        enriched.append({
            "title": idea.get("title", ""),
            "description": idea.get("description", ""),
            "pillar_id": str(pillar.id) if pillar else None,
            "pillar_name": pillar.name if pillar else "",
            "template_id": str(template.id) if template else None,
            "template_name": template.name if template else "",
            "priority": idea.get("priority", "medium"),
            "tags": idea.get("tags", []),
            "source_urls": idea.get("source_urls", []),
            "research_insight": idea.get("research_insight", ""),
        })

    return enriched
