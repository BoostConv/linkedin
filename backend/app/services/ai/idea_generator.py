"""AI-powered idea generator — suggests post topics based on pillars, trends, and expertise.

Generates a batch of post ideas tailored to Sébastien's expertise and audience,
taking into account pillar rotation and recent publications to avoid repetition.
"""
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

import anthropic
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.pillar import Pillar
from app.models.post import Post
from app.models.idea import Idea
from app.models.template import PostTemplate
from app.models.product import Product
from app.api.routes.auth import DEFAULT_USER_ID

settings = get_settings()


async def generate_idea_bank(
    db: AsyncSession,
    count: int = 10,
    focus_pillar_id: UUID | None = None,
) -> list[dict]:
    """Generate a batch of post ideas using AI.

    Takes into account:
    - Available pillars and their weights
    - Recent posts to avoid repetition
    - Current trends in CRO/e-commerce
    - Sébastien's expertise areas

    Args:
        db: Database session
        count: Number of ideas to generate
        focus_pillar_id: Optional pillar to focus on

    Returns:
        List of idea dicts with: title, description, pillar, template, angle, priority
    """
    # Load pillars
    pillars_result = await db.execute(
        select(Pillar).where(Pillar.is_active.is_(True)).order_by(Pillar.display_order)
    )
    pillars = list(pillars_result.scalars().all())

    # Load templates
    templates_result = await db.execute(
        select(PostTemplate).where(PostTemplate.is_active.is_(True)).order_by(PostTemplate.display_order)
    )
    templates = list(templates_result.scalars().all())

    # Load recent posts (last 30 days) to avoid repetition
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    recent_posts_result = await db.execute(
        select(Post.content, Post.hook)
        .where(Post.user_id == DEFAULT_USER_ID, Post.created_at >= cutoff)
        .order_by(Post.created_at.desc())
        .limit(20)
    )
    recent_posts = recent_posts_result.all()
    recent_hooks = [r.hook for r in recent_posts if r.hook]

    # Load existing ideas to avoid duplicates
    existing_ideas_result = await db.execute(
        select(Idea.raw_input)
        .where(Idea.user_id == DEFAULT_USER_ID, Idea.status.in_(["new", "drafting", "planned"]))
        .limit(30)
    )
    existing_ideas = [r.raw_input[:100] for r in existing_ideas_result.all()]

    # Build context
    pillar_list = "\n".join(
        f"- {p.name} (poids: {p.weight}): {p.description}"
        for p in pillars
    )

    template_list = "\n".join(
        f"- {t.name}: {t.when_to_use}"
        for t in templates
    )

    recent_hooks_str = "\n".join(f"- {h}" for h in recent_hooks[:10]) if recent_hooks else "Aucun post récent."

    existing_ideas_str = "\n".join(f"- {i}" for i in existing_ideas[:15]) if existing_ideas else "Aucune idée en cours."

    # Load products
    products_result = await db.execute(
        select(Product).where(Product.is_active.is_(True)).order_by(Product.display_order)
    )
    products = list(products_result.scalars().all())

    products_str = ""
    if products:
        products_str = "\n\n=== PRODUITS/SERVICES BOOST CONVERSION À PROMOUVOIR ===\n" + "\n".join(
            f"- {p.name}: {p.tagline}\n  Pain points: {', '.join(p.pain_points or [])}\n  CTA: {p.cta_text or 'N/A'}"
            for p in products
        )

    focus_instruction = ""
    if focus_pillar_id:
        for p in pillars:
            if p.id == focus_pillar_id:
                focus_instruction = f"\nCONSIGNE SPÉCIALE : Concentre-toi principalement sur le pilier '{p.name}'. Au moins 60% des idées doivent concerner ce pilier."
                break

    prompt = f"""Tu es l'assistant éditorial de Sébastien Tortu, fondateur de Boost Conversion (agence CRO/post-clic pour marques e-commerce DTC 5-50M€, basée à Paris). Il a 35 000 abonnés LinkedIn.

Son audience : fondateurs DTC/e-commerce et CMO e-commerce. Des décideurs qui veulent des résultats concrets, pas de la théorie.

Son expertise Boost Conversion :
- Stratégie post-clic complète (diagnostic marque, data-driven, ICE scoring)
- Master Persona et personas exploratoires
- Message match et parcours utilisateur
- Quiz funnels et segmentation
- Landing pages et optimisation de conversion
- Créa/statics IA pour publicités
- Whitelisting et contenu tiers
- Tests A/B et expérimentation

OBJECTIF BUSINESS : Chaque post doit, directement ou indirectement, convaincre des marques e-commerce qui investissent en ads de faire appel à Boost Conversion pour la gestion de leur post-clic (landing pages, A/B tests, quiz funnels, whitelisting, etc.)
{products_str}

Génère {count} idées de posts LinkedIn DIFFÉRENTES et CONCRÈTES pour Sébastien.

=== PILIERS DE CONTENU ===
{pillar_list}

=== TEMPLATES VIRAUX DISPONIBLES ===
{template_list}

=== ACCROCHES RÉCENTES (à ne PAS répéter) ===
{recent_hooks_str}

=== IDÉES DÉJÀ EN COURS (à ne PAS dupliquer) ===
{existing_ideas_str}
{focus_instruction}

=== CONSIGNES ===
- Chaque idée doit être SPÉCIFIQUE et ACTIONNABLE (pas de vagues "parler de CRO")
- Au moins 2-3 idées doivent être liées directement à un produit/service Boost Conversion
- Inclus des angles originaux, des opinions tranchées, des données chiffrées quand possible
- Varie les piliers (sauf si consigne spéciale) en respectant les poids
- Varie les templates
- Pense aux tendances actuelles du e-commerce et du marketing digital en 2026
- Pense aux sujets qui génèrent du débat et de l'engagement
- Inclus des sujets "coulisses/entrepreneuriat" (le 20% perso)

=== SCORING DE PRIORITÉ (TRÈS IMPORTANT — sois strict et distribue bien) ===
Sur {count} idées, tu DOIS respecter cette répartition :
- "high" : MAX 2-3 idées (20-30%). Réservé UNIQUEMENT aux idées qui cochent AU MOINS 3 critères parmi :
  1. Lien DIRECT avec un service Boost Conversion (quiz funnel, landing page, A/B test)
  2. Données chiffrées concrètes ou étude de cas réel
  3. Sujet tendance / actualité chaude du moment
  4. Potentiel de débat / opinion clivante forte
  5. Angle jamais vu dans les posts récents
- "medium" : 4-5 idées (40-50%). Bonnes idées solides, 1-2 critères ci-dessus.
- "low" : 2-3 idées (20-30%). Idées correctes mais génériques, déjà couvertes partiellement, ou sujets "coulisses" moins business.

NE METS PAS tout en "high". Si tu hésites entre high et medium, mets medium.

Réponds UNIQUEMENT en JSON avec cette structure :
[
  {{
    "title": "Titre court de l'idée (max 10 mots)",
    "description": "Description détaillée de ce que le post devrait couvrir (3-4 phrases). Inclus les données/angles/exemples à utiliser.",
    "pillar_name": "Nom du pilier",
    "template_name": "Nom du template suggéré",
    "priority": "high/medium/low",
    "priority_reason": "Justification en 1 phrase de pourquoi cette priorité",
    "tags": ["tag1", "tag2"]
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

    enriched_ideas = []
    for idea in ideas:
        pillar_name = idea.get("pillar_name", "")
        template_name = idea.get("template_name", "")

        # Find matching pillar
        pillar = pillar_map.get(pillar_name.lower())
        if not pillar:
            # Fuzzy match
            for key, p in pillar_map.items():
                if pillar_name.lower() in key or key in pillar_name.lower():
                    pillar = p
                    break
            if not pillar:
                pillar = pillars[0]

        # Find matching template
        template = template_map.get(template_name.lower())
        if not template:
            for key, t in template_map.items():
                if template_name.lower() in key or key in template_name.lower():
                    template = t
                    break
            if not template:
                template = templates[0]

        enriched_ideas.append({
            "title": idea.get("title", ""),
            "description": idea.get("description", ""),
            "pillar_id": str(pillar.id),
            "pillar_name": pillar.name,
            "template_id": str(template.id),
            "template_name": template.name,
            "priority": idea.get("priority", "medium"),
            "tags": idea.get("tags", []),
        })

    return enriched_ideas


async def save_generated_ideas(
    db: AsyncSession,
    ideas: list[dict],
) -> int:
    """Save generated ideas to the database.

    Returns:
        Number of ideas saved
    """
    saved = 0
    for idea_data in ideas:
        idea = Idea(
            user_id=DEFAULT_USER_ID,
            input_type="raw_idea",
            raw_input=f"{idea_data['title']}\n\n{idea_data['description']}",
            suggested_pillar_id=idea_data.get("pillar_id"),
            suggested_template_id=idea_data.get("template_id"),
            suggested_angle=idea_data.get("description"),
            priority=idea_data.get("priority", "medium"),
            tags={
                "tags": idea_data.get("tags", []),
                "source": "ai_generated",
                "pillar": idea_data.get("pillar_name"),
                "template": idea_data.get("template_name"),
            },
        )
        db.add(idea)
        saved += 1

    await db.commit()
    return saved
