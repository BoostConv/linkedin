"""LinkedIn analytics collector."""
import httpx

LINKEDIN_REST_BASE = "https://api.linkedin.com/rest"


async def get_post_stats(access_token: str, linkedin_post_id: str) -> dict:
    """Fetch analytics for a specific LinkedIn post.

    Uses the LinkedIn Analytics API to get impressions, likes, comments, etc.
    """
    async with httpx.AsyncClient() as client:
        # Get post statistics
        response = await client.get(
            f"{LINKEDIN_REST_BASE}/socialMetadata/{linkedin_post_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
                "LinkedIn-Version": "202401",
            },
        )

        if response.status_code == 404:
            return {"impressions": 0, "likes": 0, "comments": 0, "shares": 0, "clicks": 0}

        response.raise_for_status()
        data = response.json()

        likes = data.get("totalShareStatistics", {}).get("likeCount", 0)
        comments = data.get("totalShareStatistics", {}).get("commentCount", 0)
        shares = data.get("totalShareStatistics", {}).get("shareCount", 0)
        impressions = data.get("totalShareStatistics", {}).get("impressionCount", 0)
        clicks = data.get("totalShareStatistics", {}).get("clickCount", 0)

        total_engagement = likes + comments + shares + clicks
        engagement_rate = total_engagement / impressions if impressions > 0 else 0.0

        return {
            "impressions": impressions,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "clicks": clicks,
            "engagement_rate": round(engagement_rate, 6),
        }
