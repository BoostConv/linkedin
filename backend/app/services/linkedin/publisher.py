"""LinkedIn post publisher using Community Management API."""
import httpx

LINKEDIN_REST_BASE = "https://api.linkedin.com/rest"


async def publish_text_post(
    access_token: str,
    person_id: str,
    content: str,
) -> dict:
    """Publish a text-only post to LinkedIn.

    Uses the LinkedIn Community Management API (Posts API).
    """
    payload = {
        "author": f"urn:li:person:{person_id}",
        "commentary": content,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{LINKEDIN_REST_BASE}/posts",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
                "LinkedIn-Version": "202401",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()

        # LinkedIn returns the post ID in the x-restli-id header
        post_id = response.headers.get("x-restli-id", "")
        return {"linkedin_post_id": post_id, "status": "published"}


async def publish_image_post(
    access_token: str,
    person_id: str,
    content: str,
    image_url: str,
) -> dict:
    """Publish a post with an image to LinkedIn.

    Step 1: Initialize image upload
    Step 2: Upload the image binary
    Step 3: Create the post with the image reference
    """
    author_urn = f"urn:li:person:{person_id}"

    async with httpx.AsyncClient() as client:
        # Step 1: Initialize upload
        init_response = await client.post(
            f"{LINKEDIN_REST_BASE}/images?action=initializeUpload",
            json={
                "initializeUploadRequest": {
                    "owner": author_urn,
                }
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
                "LinkedIn-Version": "202401",
                "Content-Type": "application/json",
            },
        )
        init_response.raise_for_status()
        init_data = init_response.json()

        upload_url = init_data["value"]["uploadUrl"]
        image_urn = init_data["value"]["image"]

        # Step 2: Download image and upload to LinkedIn
        img_response = await client.get(image_url)
        img_response.raise_for_status()

        await client.put(
            upload_url,
            content=img_response.content,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/octet-stream",
            },
        )

        # Step 3: Create post with image
        payload = {
            "author": author_urn,
            "commentary": content,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "content": {
                "media": {
                    "id": image_urn,
                }
            },
            "lifecycleState": "PUBLISHED",
        }

        response = await client.post(
            f"{LINKEDIN_REST_BASE}/posts",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
                "LinkedIn-Version": "202401",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()

        post_id = response.headers.get("x-restli-id", "")
        return {"linkedin_post_id": post_id, "status": "published"}


async def publish_document_post(
    access_token: str,
    person_id: str,
    content: str,
    document_bytes: bytes,
    document_title: str = "Carrousel",
) -> dict:
    """Publish a post with a PDF document (carousel) to LinkedIn.

    Step 1: Initialize document upload
    Step 2: Upload the PDF binary
    Step 3: Create the post with the document reference
    """
    author_urn = f"urn:li:person:{person_id}"

    async with httpx.AsyncClient() as client:
        # Step 1: Initialize upload
        init_response = await client.post(
            f"{LINKEDIN_REST_BASE}/documents?action=initializeUpload",
            json={
                "initializeUploadRequest": {
                    "owner": author_urn,
                }
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
                "LinkedIn-Version": "202401",
                "Content-Type": "application/json",
            },
        )
        init_response.raise_for_status()
        init_data = init_response.json()

        upload_url = init_data["value"]["uploadUrl"]
        document_urn = init_data["value"]["document"]

        # Step 2: Upload PDF
        await client.put(
            upload_url,
            content=document_bytes,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/pdf",
            },
        )

        # Step 3: Create post with document
        payload = {
            "author": author_urn,
            "commentary": content,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "content": {
                "media": {
                    "id": document_urn,
                    "title": document_title,
                }
            },
            "lifecycleState": "PUBLISHED",
        }

        response = await client.post(
            f"{LINKEDIN_REST_BASE}/posts",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
                "LinkedIn-Version": "202401",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()

        post_id = response.headers.get("x-restli-id", "")
        return {"linkedin_post_id": post_id, "status": "published"}
