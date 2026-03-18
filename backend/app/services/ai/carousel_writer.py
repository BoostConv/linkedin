"""AI service to generate carousel slide content from a topic."""
import json

import anthropic

from app.config import get_settings

settings = get_settings()


async def generate_carousel_content(
    topic: str,
    pillar_name: str,
    num_slides: int = 8,
) -> list[dict]:
    """Generate carousel slide content using Claude.

    Returns a list of slide dicts with type, title, body, etc.
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    prompt = f"""Génère le contenu d'un carrousel LinkedIn de {num_slides} slides sur ce sujet :

Sujet : {topic}
Pilier : {pillar_name}

Le carrousel est pour Sébastien Tortu, fondateur de Boost Conversion (agence CRO e-commerce).
Audience : fondateurs DTC et CMO e-commerce.

Génère un JSON array avec {num_slides} objets. Chaque objet a ces champs :
- "slide_type": "title" (slide 1), "content" (slides du milieu), "stat" (pour les chiffres marquants), "cta" (dernier slide)
- "title": titre court et percutant (max 60 caractères)
- "body": texte du slide (max 150 caractères, seulement pour type "content")
- "stat_number": le chiffre (seulement pour type "stat", ex: "97%", "+340%", "3x")
- "stat_label": ce que le chiffre représente (seulement pour type "stat")
- "subtitle": sous-titre (pour title slide) ou texte du bouton CTA (pour cta slide)

Règles :
- Slide 1 = title (accroche qui donne envie de swiper)
- Slides 2-{num_slides - 1} = mix de "content" et "stat" (1 idée par slide, concis)
- Slide {num_slides} = cta (appel à l'action)
- Ton direct, pas de jargon, chiffres concrets quand possible
- PAS de structure "Ce n'est pas X. C'est Y."
- Phrases naturelles, pas robotiques

Réponds UNIQUEMENT avec le JSON array, sans commentaire."""

    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    # Handle markdown wrapping
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
        response_text = response_text.strip()

    return json.loads(response_text)
