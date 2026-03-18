"""Tests for ideas API routes."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestIdeasAPI:
    async def test_create_idea_raw(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/ideas/",
            json={
                "raw_input": "Post sur l'impact du CRO sur le CAC des marques DTC",
                "input_type": "raw_idea",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["raw_input"].startswith("Post sur")
        assert data["status"] in ("new", "analyzed")

    async def test_create_idea_url(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/ideas/",
            json={
                "raw_input": "https://example.com/article-cro",
                "input_type": "url",
                "source_url": "https://example.com/article-cro",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

    async def test_list_ideas(self, client: AsyncClient, auth_headers: dict):
        # Create one first
        await client.post(
            "/api/ideas/",
            json={"raw_input": "Idée test", "input_type": "raw_idea"},
            headers=auth_headers,
        )
        response = await client.get("/api/ideas/", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1

    async def test_archive_idea(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/ideas/",
            json={"raw_input": "Idée à archiver", "input_type": "raw_idea"},
            headers=auth_headers,
        )
        idea_id = resp.json()["id"]

        response = await client.put(
            f"/api/ideas/{idea_id}",
            json={"status": "archived"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "archived"
