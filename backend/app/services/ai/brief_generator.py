"""Generate multiple post ideas from a single brief/topic.

Given a brief (a topic, an observation, a question), generates several different
post idea angles that Sébastien can choose from. Each idea gets a different template,
angle, and hook approach.
"""
import json
import anthropic
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.pillar import Pillar
from app.models.template import PostTemplate
from app.models.product import Product

settings = get_settings()


async def generate_ideas_from_brief(
    db: AsyncSession,
    brief: str,
    count: int = 6,
    channel: str = "linkedin",
) -> list[dict]:
    """Generate multiple post idea variations from a single brief.

    Args:
        db: Database session
        brief: The user's brief/topic/observation
        count: Number of idea variations to generate (default 6)
        channel: Target channel - "linkedin", "newsletter", or "both"

    Returns:
        List of idea dicts with: title, description, pillar_name, template_name,
        hook_preview, priority, tags, channel
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

    # Load products
    products_result = await db.execute(
        select(Product).where(Product.is_active.is_(True))
    )
    products = list(products_result.scalars().all())

    pillar_list = "\n".join(
        f"- {p.name} (poids: {p.weight}): {p.description}"
        for p in pillars
    )

    template_list = "\n".join(
        f"- {t.name}: {t.when_to_use}"
        for t in templates
    )

    products_str = ""
    if products:
        products_str = "\n\n=== PRODUITS/SERVICES BOOST CONVERSION ===\n" + "\n".join(
            f"- {p.name}: {p.tagline} | CTA: {p.cta_text or 'N/A'}"
            for p in products
        )

    channel_instruction = ""
    if channel == "newsletter":
        channel_instruction = """
CANAL : Newsletter (pas LinkedIn)
- Le format newsletter est plus long et plus détaillé qu'un post LinkedIn
- On peut inclure des sections, des liens, des images
- Le ton est toujours conversationnel mais peut être plus approfondi
- Inclure des CTAs vers les produits/services ou vers un appel"""
    elif channel == "both":
        channel_instruction = """
CANAL : LinkedIn + Newsletter
- Pour chaque idée, indique si elle convient mieux pour LinkedIn, newsletter, ou les deux
- Les idées LinkedIn sont courtes et percutantes
- Les idées newsletter peuvent être plus longues et détaillées"""

    prompt = f"""Tu es l'assistant éditorial de Sébastien Tortu, fondateur de Boost Conversion (agence CRO/post-clic pour marques e-commerce DTC 5-50M€, Paris, 35K abonnés LinkedIn).

Sébastien te donne ce brief :

---
{brief}
---

{channel_instruction}

À partir de CE SEUL BRIEF, génère {count} ANGLES DIFFÉRENTS pour en faire des posts percutants.

=== PILIERS DE CONTENU ===
{pillar_list}

=== TEMPLATES VIRAUX ===
{template_list}
{products_str}

=== CONSIGNES ===
- Chaque idée doit prendre un ANGLE DIFFÉRENT sur le même sujet
- Varie les templates (pas 2x le même)
- Varie les tons : opinion tranchée, retour d'expérience, data/stats, histoire, éducatif...
- Pour chaque idée, propose une ACCROCHE (hook) concrète de 1-2 lignes
- L'objectif business reste : convaincre des marques e-commerce de bosser avec Boost Conversion
- Classe les idées par potentiel d'impact

=== SCORING DE PRIORITÉ (sois strict et distribue bien) ===
Sur {count} angles, répartis comme suit :
- "high" : MAX 1-2 angles. UNIQUEMENT si l'angle a un potentiel viral clair (opinion clivante, data choc, lien direct service Boost Conversion + actualité chaude)
- "medium" : 2-3 angles. Bons angles solides avec un potentiel d'engagement correct
- "low" : 1-2 angles. Angles intéressants mais plus classiques ou éducatifs

NE METS PAS tout en "high". Si tu hésites, mets "medium".

Réponds UNIQUEMENT en JSON :
[
  {{
    "title": "Titre court résumant l'angle (max 10 mots)",
    "description": "Description de l'angle et ce que le post devrait couvrir (3-4 phrases)",
    "pillar_name": "Nom du pilier",
    "template_name": "Nom du template",
    "hook_preview": "L'accroche concrète du post (1-2 lignes, prête à poster)",
    "priority": "high/medium/low",
    "priority_reason": "Justification en 1 phrase",
    "tags": ["tag1", "tag2"],
    "channel": "linkedin/newsletter/both"
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
            "hook_preview": idea.get("hook_preview", ""),
            "priority": idea.get("priority", "medium"),
            "tags": idea.get("tags", []),
            "channel": idea.get("channel", channel),
        })

    return enriched
