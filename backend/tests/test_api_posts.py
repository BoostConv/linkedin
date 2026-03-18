"""Tests for posts API routes."""
import pytest
from httpx import AsyncClient

from app.models.post import Post


@pytest.mark.asyncio
class TestPostsAPI:
    async def test_list_posts_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/posts/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    async def test_create_post(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/posts/",
            json={
                "content": "Mon post test sur le CRO e-commerce.",
                "format": "text",
                "status": "draft",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Mon post test sur le CRO e-commerce."
        assert data["status"] == "draft"

    async def test_get_post(self, client: AsyncClient, auth_headers: dict, test_post: Post):
        response = await client.get(f"/api/posts/{test_post.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_post.id)

    async def test_update_post(self, client: AsyncClient, auth_headers: dict, test_post: Post):
        response = await client.put(
            f"/api/posts/{test_post.id}",
            json={"status": "approved"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"

    async def test_delete_post(self, client: AsyncClient, auth_headers: dict, test_post: Post):
        response = await client.delete(f"/api/posts/{test_post.id}", headers=auth_headers)
        assert response.status_code == 200

        # Verify deleted
        response = await client.get(f"/api/posts/{test_post.id}", headers=auth_headers)
        assert response.status_code == 404

    async def test_filter_by_status(self, client: AsyncClient, auth_headers: dict, test_post: Post):
        response = await client.get("/api/posts/?status=draft", headers=auth_headers)
        assert response.status_code == 200
        posts = response.json()
        assert all(p["status"] == "draft" for p in posts)

    async def test_unauthorized(self, client: AsyncClient):
        response = await client.get("/api/posts/")
        assert response.status_code == 401
