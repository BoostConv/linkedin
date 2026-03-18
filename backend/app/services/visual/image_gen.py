"""Image generation service using OpenAI DALL-E 3."""
import httpx
from openai import OpenAI

from app.config import get_settings

settings = get_settings()


async def generate_image(
    prompt: str,
    style: str = "natural",
    size: str = "1024x1024",
) -> str:
    """Generate an image using DALL-E 3.

    Args:
        prompt: Description of the image to generate
        style: "natural" or "vivid"
        size: "1024x1024", "1792x1024", or "1024x1792"

    Returns:
        URL of the generated image
    """
    client = OpenAI(api_key=settings.openai_api_key)

    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        style=style,
        quality="standard",
        n=1,
    )

    return response.data[0].url


def build_image_prompt(
    post_content: str,
    image_type: str = "illustration",
) -> str:
    """Build a DALL-E prompt from post content and desired style.

    Args:
        post_content: The LinkedIn post text
        image_type: "illustration", "data_viz", "before_after", "quote_bg", "portrait_bg"
    """
    base_style = (
        "Professional, clean, modern design. "
        "Corporate blue color palette (#1E40AF, #3B82F6). "
        "Minimalist with bold typography feel. "
        "No text or letters in the image. "
        "High quality, suitable for LinkedIn. "
    )

    # Extract the core topic from the post (first 200 chars)
    topic = post_content[:200].replace("\n", " ").strip()

    prompts = {
        "illustration": (
            f"Create a professional illustration representing this concept: {topic}. "
            f"{base_style}"
            "Abstract geometric shapes and clean lines. "
        ),
        "data_viz": (
            f"Create an abstract data visualization graphic related to: {topic}. "
            f"{base_style}"
            "Charts, graphs, upward trends, analytics dashboard aesthetic. "
        ),
        "before_after": (
            f"Create a split image showing transformation, related to: {topic}. "
            f"{base_style}"
            "Left side darker/chaotic, right side bright/organized. Clear visual contrast. "
        ),
        "quote_bg": (
            "Create an abstract professional background suitable for overlaying text. "
            f"{base_style}"
            "Subtle gradients, geometric patterns, enough contrast for white text overlay. "
        ),
        "portrait_bg": (
            "Create a professional background for a business portrait photo. "
            f"{base_style}"
            "Blurred office/modern workspace, bokeh effect, warm lighting. "
        ),
    }

    return prompts.get(image_type, prompts["illustration"])
