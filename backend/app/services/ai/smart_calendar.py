"""Smart calendar service — auto-generate content plan for upcoming days."""
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.pillar import Pillar
from app.models.template import PostTemplate
from app.models.post import Post
from app.models.idea import Idea
from app.services.ai.rotation import get_next_pillar, get_pillar_balance
from app.services.ml.model import get_model_meta

settings = get_settings()


async def generate_content_plan(
    db: AsyncSession,
    user_id: UUID,
    days: int = 7,
) -> list[dict]:
    """Generate a content plan for the next N days.

    Uses pillar rotation, available ideas, ML insights, and trends
    to propose a daily content calendar.

    Returns a list of day plans with pillar, template, topic, and suggested format.
    """
    # Gather context
    balance = await get_pillar_balance(db, user_id)

    # Get pillars
    result = await db.execute(
        select(Pillar).where(Pillar.is_active.is_(True)).order_by(Pillar.display_order)
    )
    pillars = list(result.scalars().all())
    pillar_map = {str(p.id): p for p in pillars}

    # Get templates
    result = await db.execute(
        select(PostTemplate).where(PostTemplate.is_active.is_(True))
    )
    templates = list(result.scalars().all())

    # Get unused ideas
    result = await db.execute(
        select(Idea).where(
            Idea.status.in_(["new", "analyzed"]),
        ).order_by(Idea.created_at.desc()).limit(20)
    )
    ideas = list(result.scalars().all())

    # Get existing scheduled posts to avoid conflicts
    now = datetime.now(timezone.utc)
    end_date = now + timedelta(days=days)
    result = await db.execute(
        select(Post).where(
            Post.user_id == user_id,
            Post.status.in_(["scheduled", "approved"]),
            Post.scheduled_at >= now,
            Post.scheduled_at <= end_date,
        )
    )
    existing_posts = list(result.scalars().all())
    existing_dates = {
        p.scheduled_at.date() for p in existing_posts if p.scheduled_at
    }

    # Get ML insights
    model_meta = await get_model_meta(db)

    # Build context for Claude
    balance_text = "\n".join(
        f"- {b['pillar_name']}: {b['actual_pct']}% (cible {b['target_pct']}%, déficit {b['deficit_pct']}%)"
        for b in balance
    )

    ideas_text = "\n".join(
        f"- [{i.priority}] {i.raw_input[:100]} (pilier suggéré: {i.suggested_pillar_id or 'aucun'})"
        for i in ideas[:10]
    )

    templates_text = "\n".join(f"- {t.name} ({t.slug}): {t.when_to_use}" for t in templates)

    ml_text = ""
    if model_meta and model_meta.get("top_features"):
        top_features = model_meta["top_features"][:5]
        ml_text = "Facteurs ML importants : " + ", ".join(f[0] for f in top_features)

    existing_text = "\n".join(
        f"- {p.scheduled_at.strftime('%A %d/%m')}: déjà planifié ({p.format})"
        for p in existing_posts
    ) or "Aucun post déjà planifié."

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    prompt = f"""Génère un plan de contenu LinkedIn pour les {days} prochains jours pour Sébastien Tortu (Boost Conversion, agence CRO e-commerce).

=== ÉQUILIBRE DES PILIERS (14 jours) ===
{balance_text}

=== IDÉES DISPONIBLES ===
{ideas_text or "Aucune idée en attente."}

=== TEMPLATES DISPONIBLES ===
{templates_text}

=== POSTS DÉJÀ PLANIFIÉS ===
{existing_text}

{f"=== INSIGHTS ML ===" + chr(10) + ml_text if ml_text else ""}

=== RÈGLES ===
- 1 post par jour, du lundi au vendredi (sauter samedi/dimanche)
- Respecter l'équilibre des piliers (prioriser ceux en déficit)
- Varier les formats (texte, carrousel, image+texte)
- Varier les templates (pas 2 fois le même d'affilée)
- Utiliser les idées disponibles quand elles correspondent
- Ne pas planifier sur les jours qui ont déjà un post
- Date de départ : {now.strftime('%A %d/%m/%Y')}

Réponds en JSON array avec pour chaque jour planifié :
[{{
  "date": "YYYY-MM-DD",
  "day_name": "Lundi",
  "pillar_name": "nom du pilier",
  "template_slug": "slug du template",
  "format": "text|carousel|image_text",
  "topic": "sujet concret et spécifique",
  "hook_idea": "idée d'accroche en 1 phrase",
  "idea_id": "UUID de l'idée utilisée, ou null"
}}]

UNIQUEMENT le JSON, sans commentaire."""

    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
        response_text = response_text.strip()

    return json.loads(response_text)


async def regenerate_day(
    db: AsyncSession,
    user_id: UUID,
    date: str,
    constraints: str | None = None,
) -> dict:
    """Regenerate the content plan for a single day with optional constraints."""
    balance = await get_pillar_balance(db, user_id)

    result = await db.execute(
        select(Pillar).where(Pillar.is_active.is_(True))
    )
    pillars = list(result.scalars().all())

    result = await db.execute(
        select(PostTemplate).where(PostTemplate.is_active.is_(True))
    )
    templates = list(result.scalars().all())

    balance_text = "\n".join(
        f"- {b['pillar_name']}: déficit {b['deficit_pct']}%"
        for b in balance
    )
    templates_text = ", ".join(t.slug for t in templates)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    prompt = f"""Propose un post LinkedIn pour le {date}.

Équilibre piliers : {balance_text}
Templates dispo : {templates_text}
{f"Contrainte : {constraints}" if constraints else ""}

JSON avec : pillar_name, template_slug, format (text|carousel|image_text), topic, hook_idea.
UNIQUEMENT le JSON."""

    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
        response_text = response_text.strip()

    return json.loads(response_text)
