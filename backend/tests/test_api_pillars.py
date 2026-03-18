"""Tests for pillars API routes."""
import pytest
from httpx import AsyncClient

from app.models.pillar import Pillar


@pytest.mark.asyncio
class TestPillarsAPI:
    async def test_list_pillars(self, client: AsyncClient, auth_headers: dict, test_pillar: Pillar):
        response = await client.get("/api/pillars/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    async def test_create_pillar(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/pillars/",
            json={
                "name": "Landing Pages",
                "slug": "landing-pages",
                "description": "Tout sur les LP",
                "weight": 20,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Landing Pages"
        assert data["slug"] == "landing-pages"

    async def test_update_pillar(self, client: AsyncClient, auth_headers: dict, test_pillar: Pillar):
        response = await client.put(
            f"/api/pillars/{test_pillar.id}",
            json={"weight": 30},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["weight"] == 30

    async def test_delete_pillar(self, client: AsyncClient, auth_headers: dict, test_pillar: Pillar):
        response = await client.delete(f"/api/pillars/{test_pillar.id}", headers=auth_headers)
        assert response.status_code == 200
