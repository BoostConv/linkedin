"""AI service to generate structured case study posts."""
import json

import anthropic

from app.config import get_settings

settings = get_settings()


async def generate_case_study(
    client_name: str,
    industry: str,
    problem: str,
    actions: str,
    results: str,
    anonymize: bool = True,
    additional_context: str | None = None,
) -> dict:
    """Generate a structured case study post.

    Args:
        client_name: Real or fictional client name
        industry: Client's industry/niche
        problem: The problem they faced
        actions: What Boost Conversion did
        results: Quantified results
        anonymize: Whether to use a fictional name
        additional_context: Extra context

    Returns:
        Dict with 'content', 'hook', 'format', 'slides' (if carousel format)
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    prompt = f"""Génère un post LinkedIn type "étude de cas" pour Sébastien Tortu (Boost Conversion, agence CRO e-commerce).

=== DONNÉES DE L'ÉTUDE ===
Client : {client_name}{" (anonymiser le nom)" if anonymize else ""}
Industrie : {industry}
Problème : {problem}
Actions menées : {actions}
Résultats : {results}
{f"Contexte supplémentaire : {additional_context}" if additional_context else ""}

=== STRUCTURE OBLIGATOIRE ===
Le post DOIT suivre cette structure :
1. ACCROCHE — Un chiffre ou résultat choc qui donne envie de lire
2. CONTEXTE — Qui est le client, son problème en 2-3 phrases
3. DIAGNOSTIC — Ce qu'on a trouvé (données, insights)
4. ACTIONS — Ce qu'on a fait concrètement (pas de jargon creux, des actions précises)
5. RÉSULTATS — Chiffres avant/après, pourcentages, impact business
6. LEÇON — Ce que tout le monde peut en retenir (1-2 phrases)
7. CTA — Question ou appel à l'action

=== RÈGLES ===
- Ton direct, entrepreneur qui pense à voix haute
- Chiffres précis systématiques
- Pas de tutoiement
- Varier longueur des phrases (courtes ET longues)
- Pas de "Ce n'est pas X. C'est Y."
- Pas de tirets cadratins
- Max 2 emojis
- Paragraphes ≤ 3 lignes

Réponds en JSON :
{{
  "content": "le post complet",
  "hook": "les 2 premières lignes (accroche)",
  "suggested_format": "text ou carousel",
  "carousel_slides": [
    {{"slide_type": "title|content|stat|cta", "title": "...", "body": "...", "stat_number": "...", "stat_label": "..."}}
  ]
}}

Le champ carousel_slides est un bonus : génère les slides même si le format suggéré est texte (comme option).
UNIQUEMENT le JSON."""

    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
        response_text = response_text.strip()

    return json.loads(response_text)
