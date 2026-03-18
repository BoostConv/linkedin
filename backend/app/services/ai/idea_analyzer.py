"""AI service to analyze ideas and suggest pillar, template, and angle."""
import json
from uuid import UUID

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.pillar import Pillar
from app.models.template import PostTemplate
from app.models.idea import Idea

settings = get_settings()


async def analyze_idea(db: AsyncSession, idea_id: UUID) -> dict:
    """Analyze an idea and suggest pillar, template, and angle.

    Updates the idea in-place with suggestions.
    """
    # Load idea
    result = await db.execute(select(Idea).where(Idea.id == idea_id))
    idea = result.scalar_one_or_none()
    if not idea:
        raise ValueError(f"Idea {idea_id} not found")

    # Load available pillars and templates
    pillars_result = await db.execute(
        select(Pillar).where(Pillar.is_active.is_(True)).order_by(Pillar.display_order)
    )
    pillars = list(pillars_result.scalars().all())

    templates_result = await db.execute(
        select(PostTemplate).where(PostTemplate.is_active.is_(True)).order_by(PostTemplate.display_order)
    )
    templates = list(templates_result.scalars().all())

    # Build pillar and template lists for the prompt
    pillar_list = "\n".join(f"- {p.name} (ID: {p.id}): {p.description}" for p in pillars)
    template_list = "\n".join(f"- {t.name} (ID: {t.id}, slug: {t.slug}): {t.description}" for t in templates)

    prompt = f"""Analyse cette idée de post LinkedIn et suggère le meilleur pilier de contenu, le meilleur template, et un angle spécifique.

=== IDÉE ===
Type: {idea.input_type}
Contenu: {idea.raw_input}
{f"URL source: {idea.source_url}" if idea.source_url else ""}
{f"Contenu scrapé: {idea.scraped_content[:500]}" if idea.scraped_content else ""}

=== PILIERS DISPONIBLES ===
{pillar_list}

=== TEMPLATES DISPONIBLES ===
{template_list}

=== SCORING DE PRIORITÉ (sois TRÈS STRICT — la majorité des idées doivent être "medium") ===
- "high" : RARE (environ 1 idée sur 5). UNIQUEMENT si TOUS ces critères sont remplis :
  1. Lien DIRECT avec un service Boost Conversion (quiz funnel, landing page, A/B test, whitelisting)
  2. ET données chiffrées concrètes (%, €, x fois)
  3. ET sujet tendance 2026 OU opinion très clivante
  Si l'un de ces 3 manque → ce n'est PAS "high".
- "medium" : LE PLUS COURANT (environ 3 idées sur 5). Bonne idée avec au moins un point fort.
- "low" : (environ 1 idée sur 5). Idée vague, générique, sans données concrètes, sujet déjà traité, ou thème "coulisses" sans lien business.

RÈGLE D'OR : en cas de doute → "medium". Tu dois être aussi exigeant qu'un éditeur en chef.

Réponds en JSON strict avec cette structure:
{{
  "suggested_pillar_id": "UUID du pilier le plus pertinent",
  "suggested_template_id": "UUID du template le plus adapté",
  "suggested_angle": "Description de l'angle à prendre pour le post (2-3 phrases)",
  "priority": "high/medium/low",
  "priority_reason": "Justification en 1 phrase de pourquoi cette priorité",
  "tags": ["tag1", "tag2", "tag3"]
}}

Réponds UNIQUEMENT avec le JSON, sans commentaire."""

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    # Parse JSON (handle potential markdown wrapping)
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]

    analysis = json.loads(response_text)

    # Update idea
    if analysis.get("suggested_pillar_id"):
        idea.suggested_pillar_id = analysis["suggested_pillar_id"]
    if analysis.get("suggested_template_id"):
        idea.suggested_template_id = analysis["suggested_template_id"]
    if analysis.get("suggested_angle"):
        idea.suggested_angle = analysis["suggested_angle"]
    if analysis.get("priority"):
        idea.priority = analysis["priority"]
    if analysis.get("tags"):
        idea.tags = {"tags": analysis["tags"]}

    await db.commit()
    await db.refresh(idea)

    return analysis
