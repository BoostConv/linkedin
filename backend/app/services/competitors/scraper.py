"""Scrape competitor LinkedIn posts using Apify."""
import httpx

from app.config import get_settings

settings = get_settings()

APIFY_LINKEDIN_SCRAPER = "curious_coder/linkedin-post-search-scraper"
APIFY_API_BASE = "https://api.apify.com/v2"


async def scrape_competitor_posts(linkedin_url: str, max_posts: int = 20) -> list[dict]:
    """Scrape recent posts from a LinkedIn profile using Apify.

    Args:
        linkedin_url: The LinkedIn profile URL to scrape.
        max_posts: Maximum number of posts to retrieve.

    Returns:
        List of dicts with post content and engagement metrics.
    """
    if not settings.apify_api_token:
        return []

    # Extract profile identifier from URL
    profile_id = linkedin_url.rstrip("/").split("/")[-1]

    async with httpx.AsyncClient(timeout=120) as client:
        # Start the actor run
        run_response = await client.post(
            f"{APIFY_API_BASE}/acts/{APIFY_LINKEDIN_SCRAPER}/runs",
            params={"token": settings.apify_api_token},
            json={
                "searchUrls": [linkedin_url],
                "deepScrape": False,
                "maxItems": max_posts,
            },
        )

        if run_response.status_code != 201:
            return []

        run_data = run_response.json()
        run_id = run_data["data"]["id"]
        dataset_id = run_data["data"]["defaultDatasetId"]

        # Wait for completion (poll every 5 seconds, max 2 minutes)
        import asyncio
        for _ in range(24):
            status_resp = await client.get(
                f"{APIFY_API_BASE}/actor-runs/{run_id}",
                params={"token": settings.apify_api_token},
            )
            status = status_resp.json()["data"]["status"]
            if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                break
            await asyncio.sleep(5)

        if status != "SUCCEEDED":
            return []

        # Fetch results
        items_resp = await client.get(
            f"{APIFY_API_BASE}/datasets/{dataset_id}/items",
            params={"token": settings.apify_api_token, "format": "json"},
        )

        if items_resp.status_code != 200:
            return []

        raw_items = items_resp.json()

        # Normalize results
        posts = []
        for item in raw_items[:max_posts]:
            posts.append({
                "content": item.get("text", ""),
                "likes": item.get("likesCount", 0) or item.get("numLikes", 0),
                "comments": item.get("commentsCount", 0) or item.get("numComments", 0),
                "shares": item.get("repostsCount", 0) or item.get("numShares", 0),
                "post_url": item.get("url", "") or item.get("postUrl", ""),
                "posted_at": item.get("postedAt") or item.get("publishedAt"),
                "post_type": item.get("type", "text"),
            })

        return posts
