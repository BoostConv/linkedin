"""Tests for auth API routes."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAuthAPI:
    async def test_register(self, client: AsyncClient):
        response = await client.post("/api/auth/register", json={
            "email": "new@boost.com",
            "password": "securepass123",
            "full_name": "New User",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_duplicate_email(self, client: AsyncClient):
        # First registration
        await client.post("/api/auth/register", json={
            "email": "dup@boost.com",
            "password": "pass123",
            "full_name": "Dup User",
        })
        # Second attempt
        response = await client.post("/api/auth/register", json={
            "email": "dup@boost.com",
            "password": "pass456",
            "full_name": "Dup User 2",
        })
        assert response.status_code == 400

    async def test_login(self, client: AsyncClient):
        # Register first
        await client.post("/api/auth/register", json={
            "email": "login@boost.com",
            "password": "mypassword",
            "full_name": "Login User",
        })
        # Login
        response = await client.post("/api/auth/login", json={
            "email": "login@boost.com",
            "password": "mypassword",
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post("/api/auth/register", json={
            "email": "wrong@boost.com",
            "password": "rightpass",
            "full_name": "Wrong User",
        })
        response = await client.post("/api/auth/login", json={
            "email": "wrong@boost.com",
            "password": "wrongpass",
        })
        assert response.status_code == 401

    async def test_me_authenticated(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@boost.com"

    async def test_me_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/auth/me")
        assert response.status_code == 401
