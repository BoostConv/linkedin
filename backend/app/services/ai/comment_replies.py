"""AI service to generate reply suggestions for LinkedIn comments."""
import json

import anthropic

from app.config import get_settings

settings = get_settings()


async def suggest_reply(
    post_content: str,
    comment_text: str,
    commenter_name: str,
    commenter_headline: str | None = None,
    is_prospect: bool = False,
) -> str:
    """Generate a reply suggestion for a comment.

    Args:
        post_content: The original post content
        comment_text: The comment to reply to
        commenter_name: Name of the commenter
        commenter_headline: LinkedIn headline of the commenter
        is_prospect: Whether this person matches our target audience

    Returns:
        Suggested reply text
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    prospect_context = ""
    if is_prospect:
        prospect_context = """
IMPORTANT : Cette personne est un prospect potentiel (fondateur DTC ou CMO e-commerce).
La réponse doit être particulièrement engageante et ouvrir une conversation.
Propose subtilement de continuer en DM si pertinent."""

    prompt = f"""Tu es Sébastien Tortu, fondateur de Boost Conversion (agence CRO e-commerce).
Tu réponds à un commentaire sur ton post LinkedIn.

=== TON POST ===
{post_content[:500]}

=== COMMENTAIRE ===
De : {commenter_name}{f" ({commenter_headline})" if commenter_headline else ""}
Contenu : {comment_text}
{prospect_context}

=== RÈGLES DE RÉPONSE ===
- Ton naturel, comme dans un échange entre pros
- Pas de "Merci pour ton commentaire" générique
- Rebondir sur un point spécifique du commentaire
- Apporter une valeur ajoutée ou une nuance
- 2-4 phrases max
- Pas de tutoiement (vouvoiement ou "on")
- Pas de formules toutes faites
- Si le commentaire est une question, y répondre directement
- Si c'est un compliment, remercier brièvement puis ajouter une insight

Réponds UNIQUEMENT avec le texte de la réponse, sans guillemets ni formatage."""

    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text.strip()


async def batch_suggest_replies(
    post_content: str,
    comments: list[dict],
) -> list[dict]:
    """Generate reply suggestions for multiple comments at once.

    Args:
        post_content: The original post content
        comments: List of dicts with 'id', 'content', 'author_name', 'author_headline', 'is_prospect'

    Returns:
        List of dicts with 'comment_id' and 'suggested_reply'
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    comments_text = ""
    for i, c in enumerate(comments[:10]):
        comments_text += (
            f"\n--- Commentaire {i + 1} (ID: {c['id']}) ---\n"
            f"De : {c['author_name']}{' [PROSPECT]' if c.get('is_prospect') else ''}\n"
            f"Contenu : {c['content']}\n"
        )

    prompt = f"""Tu es Sébastien Tortu, fondateur de Boost Conversion (agence CRO e-commerce).
Tu dois répondre à plusieurs commentaires sur ton post LinkedIn.

=== TON POST ===
{post_content[:500]}

=== COMMENTAIRES ===
{comments_text}

=== RÈGLES ===
- Ton naturel, comme dans un échange entre pros
- Rebondir sur un point spécifique
- 2-4 phrases par réponse
- Pas de tutoiement
- Pour les [PROSPECT], être plus engageant et ouvrir la conversation
- Varier les réponses (pas de formules répétitives)

Réponds en JSON array :
[{{"comment_id": "...", "suggested_reply": "..."}}]

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
