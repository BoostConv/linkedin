"""Suggest visual accompaniment for a LinkedIn post."""
import json
import anthropic
from app.config import get_settings

settings = get_settings()


async def suggest_visual_for_post(content: str, pillar_name: str = "") -> dict:
    """Analyze a post and suggest the best visual format.

    Returns:
        Dict with: visual_type, description, carousel_suggestion (if carousel recommended)
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    prompt = f"""Tu es le directeur créatif de Sébastien Tortu (Boost Conversion, agence CRO post-clic).

Analyse ce post LinkedIn et suggère le meilleur accompagnement visuel pour maximiser l'engagement.

=== POST ===
{content}

=== PILIER ===
{pillar_name or "Non spécifié"}

=== OPTIONS VISUELLES ===
1. **Carrousel PDF** — Idéal pour : listes, frameworks, étapes, comparaisons, études de cas. 8-10 slides format carré.
2. **Image statique** — Idéal pour : stat choc, citation, avant/après, schéma simple.
3. **Texte seul** — Parfois le texte suffit, pas besoin de forcer un visuel.

Réponds UNIQUEMENT en JSON :
{{
  "visual_type": "carousel" | "image" | "text_only",
  "reasoning": "Pourquoi ce format (1 phrase)",
  "visual_description": "Description précise du visuel à créer",
  "carousel_slides": [
    {{
      "slide_number": 1,
      "title": "Titre de la slide",
      "content": "Contenu principal",
      "visual_note": "Note sur le design de cette slide"
    }}
  ] // seulement si visual_type == "carousel", sinon null
}}"""

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
