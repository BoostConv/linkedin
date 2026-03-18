"""OpenAI helper for analytical tasks (GPT-4o-mini).

Used for classification, scoring, and analysis tasks where cost matters
more than creative quality. Creative tasks stay on Claude.
"""
from openai import OpenAI
from app.config import get_settings

settings = get_settings()

ANALYTICAL_MODEL = "gpt-4o-mini"


def openai_complete(system: str, user: str, max_tokens: int = 4096) -> str:
    """Call GPT-4o-mini for analytical tasks."""
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=ANALYTICAL_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=max_tokens,
        temperature=0.3,  # Lower temp for analytical consistency
    )
    return response.choices[0].message.content.strip()
