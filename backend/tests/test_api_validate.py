"""Tests for the /ai/validate endpoint."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestValidateAPI:
    async def test_validate_clean(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/ai/validate",
            json={"content": "J'ai analysé 47 landing pages. Le constat est clair."},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert data["passed"] is True

    async def test_validate_with_issues(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/ai/validate",
            json={
                "content": (
                    "Ce n'est pas un problème de trafic. C'est un problème de conversion.\n"
                    "Ce n'est pas le design — c'est la clarté.\n"
                    "Plongeons dans le vif du sujet."
                )
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["issues"]) > 0
        assert data["score"] < 100
