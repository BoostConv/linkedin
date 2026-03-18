"""Auto-select pillar and template based on topic/idea content.

Uses Claude to analyze the idea and match it to the best pillar + template,
taking into account the pillar rotation algorithm for balanced content.
"""
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.services.ai.openai_helper import openai_complete
from app.models.pillar import Pillar
from app.models.template import PostTemplate
from app.models.product import Product
from app.services.ai.rotation import get_next_pillar

settings = get_settings()


async def auto_select_pillar_and_template(
    db: AsyncSession,
    idea_text: str,
    user_id: UUID,
    source_url: str | None = None,
) -> dict:
    """Analyze an idea and auto-select the best pillar + template.

    Uses Claude to match the idea's topic to pillars and templates,
    while factoring in the rotation algorithm's recommendation.

    Returns:
        dict with keys: pillar_id, pillar_name, template_id, template_name,
                        suggested_angle, reasoning
    """
    # Load all active pillars
    pillar_result = await db.execute(
        select(Pillar).where(Pillar.is_active.is_(True)).order_by(Pillar.display_order)
    )
    pillars = list(pillar_result.scalars().all())
    if not pillars:
        raise ValueError("Aucun pilier actif configuré")

    # Load all active templates
    template_result = await db.execute(
        select(PostTemplate).where(PostTemplate.is_active.is_(True)).order_by(PostTemplate.display_order)
    )
    templates = list(template_result.scalars().all())
    if not templates:
        raise ValueError("Aucun template actif configuré")

    # Get the rotation recommendation
    try:
        recommended_pillar = await get_next_pillar(db, user_id)
        rotation_hint = f"L'algorithme de rotation recommande le pilier '{recommended_pillar.name}' (ID: {recommended_pillar.id}) car il est sous-représenté dans les publications récentes. Privilégie ce pilier si le sujet s'y prête."
    except ValueError:
        rotation_hint = "Pas de recommandation de rotation disponible."

    # Load products
    products_result = await db.execute(
        select(Product).where(Product.is_active.is_(True)).order_by(Product.display_order)
    )
    products = list(products_result.scalars().all())

    products_desc = ""
    if products:
        products_desc = "\n\n=== PRODUITS/SERVICES BOOST CONVERSION ===\n" + "\n".join(
            f"- {p.name}: {p.tagline} | Audience: {p.target_audience} | CTA: {p.cta_text or 'N/A'}"
            for p in products
        )
        products_desc += "\n\nSi le sujet est lié à un produit, intègre naturellement la mention du produit et son CTA dans l'angle suggéré."

    # Build the prompt for Claude to pick pillar + template
    pillars_desc = "\n".join(
        f"- ID: {p.id} | Nom: {p.name} | Description: {p.description} | Templates préférés: {p.preferred_templates or 'tous'}"
        for p in pillars
    )

    templates_desc = "\n".join(
        f"- ID: {t.id} | Nom: {t.name} | Slug: {t.slug} | Quand l'utiliser: {t.when_to_use}"
        for t in templates
    )

    system_prompt = """Tu es un assistant éditorial pour Sébastien Tortu, fondateur de Boost Conversion (agence CRO e-commerce).
Ta mission : analyser une idée de post LinkedIn et déterminer le meilleur pilier de contenu ET le meilleur template viral à utiliser.

Tu dois répondre UNIQUEMENT en JSON valide, sans aucun texte avant ou après. Format exact :
{
  "pillar_id": "uuid-du-pilier",
  "template_id": "uuid-du-template",
  "suggested_angle": "L'angle spécifique à prendre pour ce post (2-3 phrases)",
  "reasoning": "Pourquoi ce pilier et ce template sont les meilleurs choix (1-2 phrases)"
}"""

    user_message = f"""Voici l'idée de post à analyser :

"{idea_text}"
{f'URL source : {source_url}' if source_url else ''}

=== PILIERS DISPONIBLES ===
{pillars_desc}

=== TEMPLATES DISPONIBLES ===
{templates_desc}

=== RECOMMANDATION DE ROTATION ===
{rotation_hint}

Choisis le pilier le plus pertinent pour ce sujet ET le template viral le plus adapté.
Si le sujet correspond au pilier recommandé par la rotation, privilégie-le.
Si le sujet ne colle vraiment pas au pilier recommandé, choisis le pilier le plus pertinent.
{products_desc}

Propose un angle spécifique et concret pour le post."""

    response_text = openai_complete(
        system=system_prompt,
        user=user_message,
        max_tokens=1024,
    )

    # Parse JSON response
    try:
        # Handle potential markdown code blocks
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        result = json.loads(response_text)
    except json.JSONDecodeError:
        # Fallback: use rotation-recommended pillar and first template
        result = {
            "pillar_id": str(pillars[0].id),
            "template_id": str(templates[0].id),
            "suggested_angle": idea_text,
            "reasoning": "Sélection par défaut (l'analyse IA n'a pas pu déterminer le meilleur match)",
        }

    # Validate that IDs exist
    pillar_ids = {str(p.id) for p in pillars}
    template_ids = {str(t.id) for t in templates}

    if result["pillar_id"] not in pillar_ids:
        result["pillar_id"] = str(pillars[0].id)
    if result["template_id"] not in template_ids:
        result["template_id"] = str(templates[0].id)

    # Add names for convenience
    for p in pillars:
        if str(p.id) == result["pillar_id"]:
            result["pillar_name"] = p.name
            break
    for t in templates:
        if str(t.id) == result["template_id"]:
            result["template_name"] = t.name
            break

    return result
