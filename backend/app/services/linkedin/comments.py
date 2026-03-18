"""LinkedIn Comments API client — fetch and reply to comments."""
import httpx

LINKEDIN_REST_BASE = "https://api.linkedin.com/rest"


async def fetch_post_comments(
    access_token: str,
    linkedin_post_id: str,
    count: int = 50,
) -> list[dict]:
    """Fetch comments on a LinkedIn post.

    Returns a list of dicts with comment data.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{LINKEDIN_REST_BASE}/socialActions/{linkedin_post_id}/comments",
            params={"count": count, "start": 0},
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
                "LinkedIn-Version": "202401",
            },
        )
        response.raise_for_status()
        data = response.json()

    comments = []
    for element in data.get("elements", []):
        actor = element.get("actor", "")
        comments.append({
            "linkedin_comment_id": element.get("$URN", element.get("id", "")),
            "author_linkedin_id": actor.split(":")[-1] if actor else "",
            "content": element.get("message", {}).get("text", ""),
            "commented_at": element.get("created", {}).get("time"),
        })

    return comments


async def reply_to_comment(
    access_token: str,
    linkedin_post_id: str,
    linkedin_comment_id: str,
    person_id: str,
    reply_text: str,
) -> dict:
    """Reply to a specific comment on a LinkedIn post."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{LINKEDIN_REST_BASE}/socialActions/{linkedin_post_id}/comments",
            json={
                "actor": f"urn:li:person:{person_id}",
                "message": {"text": reply_text},
                "parentComment": linkedin_comment_id,
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
                "LinkedIn-Version": "202401",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        reply_id = response.headers.get("x-restli-id", "")
        return {"linkedin_reply_id": reply_id, "status": "sent"}


async def get_commenter_profile(
    access_token: str,
    person_id: str,
) -> dict:
    """Get basic profile info for a commenter to help prioritize."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{LINKEDIN_REST_BASE}/people/(id:{person_id})",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Restli-Protocol-Version": "2.0.0",
                    "LinkedIn-Version": "202401",
                },
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "name": f"{data.get('firstName', '')} {data.get('lastName', '')}".strip(),
                    "headline": data.get("headline", ""),
                }
    except Exception:
        pass
    return {"name": "", "headline": ""}
