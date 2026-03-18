"""Content generation engine using Claude API.

This is the core of the LinkedIn automation tool. It generates posts
based on pillars, templates, writing rules, and anti-AI rules.
"""
import json
from uuid import UUID

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.pillar import Pillar
from app.models.template import PostTemplate
from app.models.writing_rule import WritingRule

settings = get_settings()


async def load_writing_context(db: AsyncSession) -> dict:
    """Load all active writing rules, organized by category."""
    result = await db.execute(
        select(WritingRule).where(WritingRule.is_active.is_(True)).order_by(WritingRule.display_order)
    )
    rules = result.scalars().all()

    context = {"tone": [], "anti_ai": [], "banned_words": [], "hook_pattern": [], "cta": []}
    for rule in rules:
        entry = {
            "name": rule.name,
            "content": rule.content,
        }
        if rule.example_good:
            entry["example_good"] = rule.example_good
        if rule.example_bad:
            entry["example_bad"] = rule.example_bad
        context.setdefault(rule.category, []).append(entry)

    return context


def build_system_prompt(
    pillar: Pillar,
    template: PostTemplate,
    writing_context: dict,
    ml_recommendations: str | None = None,
) -> str:
    """Build the system prompt for Claude with all rules and context."""

    tone_rules = "\n".join(
        f"- {r['name']}: {r['content']}"
        + (f"\n  BON EXEMPLE: {r['example_good']}" if r.get("example_good") else "")
        + (f"\n  MAUVAIS EXEMPLE: {r['example_bad']}" if r.get("example_bad") else "")
        for r in writing_context.get("tone", [])
    )

    anti_ai_rules = "\n".join(
        f"- {r['name']}: {r['content']}"
        + (f"\n  MAUVAIS EXEMPLE: {r['example_bad']}" if r.get("example_bad") else "")
        for r in writing_context.get("anti_ai", [])
    )

    banned_words_rules = "\n".join(
        f"- {r['content']}" for r in writing_context.get("banned_words", [])
    )

    template_steps = "\n".join(
        f"{i+1}. {step['name'].upper()}: {step['description']}"
        for i, step in enumerate(template.structure.get("steps", []))
    )

    system = f"""Tu es Sébastien Tortu, fondateur de Boost Conversion, agence CRO spécialisée dans la stratégie post-clic pour les marques e-commerce DTC entre 5M et 50M€. Tu as 35 000 abonnés LinkedIn.

Tu écris un post LinkedIn pour ton audience de fondateurs DTC/e-commerce et CMO e-commerce.

=== PILIER DE CONTENU ===
Pilier: {pillar.name}
Description: {pillar.description}

=== TEMPLATE À SUIVRE ===
Template: {template.name}
Description: {template.description}

Structure du post:
{template_steps}

Instructions spécifiques pour ce template:
{template.prompt_instructions}

=== TON & STYLE (IMPÉRATIF) ===
{tone_rules}

=== RÈGLES ANTI-IA (TOLÉRANCE ZÉRO) ===
{anti_ai_rules}

=== MOTS ET EXPRESSIONS BANNIS ===
{banned_words_rules}

=== CE QUI REND UN TEXTE HUMAIN ===
- Des détails spécifiques qui ne peuvent pas être inventés (un chiffre précis, un outil nommé, un moment daté)
- Des phrases qui commencent par "Et" ou "Mais" ou "Parce que"
- Des parenthèses qui ajoutent un commentaire personnel, une nuance, un doute
- Un mélange de phrases courtes ET de phrases longues qui respirent
- Des moments de vulnérabilité ou d'hésitation ("je suis pas sûr que...", "on verra si ça tient dans 3 mois")
- Des opinions tranchées assumées à la première personne
- Des détours, des digressions courtes
- L'absence de structure parfaitement symétrique

=== FORMAT DE SORTIE ===
Génère UNIQUEMENT le texte du post LinkedIn, prêt à être copié-collé. Pas de commentaire, pas d'explication, pas de titre, pas de guillemets autour du post.
Le post doit faire entre 800 et 2000 caractères.
Utilise des sauts de ligne pour aérer (une ligne vide entre les paragraphes).
Max 2 emojis dans tout le post.
PAS de tutoiement. Privilégier "on" ou le vouvoiement quand nécessaire.
PAS de hashtags à la fin."""

    if ml_recommendations:
        system += f"""

=== RECOMMANDATIONS ML (basées sur la performance des posts précédents) ===
{ml_recommendations}"""

    return system


async def generate_post(
    db: AsyncSession,
    pillar_id: UUID,
    template_id: UUID,
    topic: str | None = None,
    additional_context: str | None = None,
    ml_recommendations: str | None = None,
) -> dict:
    """Generate a LinkedIn post using Claude API.

    Returns:
        dict with keys: content, hook, hook_pattern, generation_prompt, generation_metadata
    """
    # Load pillar and template
    pillar_result = await db.execute(select(Pillar).where(Pillar.id == pillar_id))
    pillar = pillar_result.scalar_one_or_none()
    if not pillar:
        raise ValueError(f"Pillar {pillar_id} not found")

    template_result = await db.execute(select(PostTemplate).where(PostTemplate.id == template_id))
    template = template_result.scalar_one_or_none()
    if not template:
        raise ValueError(f"Template {template_id} not found")

    # Load writing rules
    writing_context = await load_writing_context(db)

    # Build prompts
    system_prompt = build_system_prompt(pillar, template, writing_context, ml_recommendations)

    user_message = f"Écris un post LinkedIn en utilisant le template '{template.name}' sur le pilier '{pillar.name}'."
    if topic:
        user_message += f"\n\nSujet/angle spécifique: {topic}"
    if additional_context:
        user_message += f"\n\nContexte additionnel: {additional_context}"

    # Call Claude API
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    content = message.content[0].text

    # Extract hook (first line or first two lines)
    lines = [l for l in content.split("\n") if l.strip()]
    hook = lines[0] if lines else ""
    if len(hook) < 50 and len(lines) > 1:
        hook = lines[0] + " " + lines[1]

    return {
        "content": content,
        "hook": hook[:200],
        "generation_prompt": user_message,
        "generation_metadata": {
            "model": settings.claude_model,
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
            "pillar": pillar.name,
            "template": template.name,
            "topic": topic,
        },
    }


async def generate_post_variants(
    db: AsyncSession,
    pillar_id: UUID,
    template_id: UUID,
    topic: str | None = None,
    count: int = 2,
) -> list[dict]:
    """Generate multiple variants of a post for A/B testing hooks."""
    variants = []
    for i in range(count):
        extra_context = None
        if i > 0:
            # Ask for a different angle on subsequent variants
            extra_context = f"Propose un angle DIFFÉRENT et une accroche DIFFÉRENTE des versions précédentes. Version {i+1}/{count}."
            if variants:
                extra_context += f"\n\nAccroche de la version précédente (À NE PAS RÉUTILISER): {variants[-1]['hook']}"

        variant = await generate_post(
            db=db,
            pillar_id=pillar_id,
            template_id=template_id,
            topic=topic,
            additional_context=extra_context,
        )
        variants.append(variant)

    return variants
