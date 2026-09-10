"""
Auth endpoint tests — register, login, refresh, logout.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "Secure1234",
            "full_name": "Test Advocate",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]["tokens"]
    assert "refresh_token" in data["data"]["tokens"]
    assert data["data"]["user"]["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    payload = {
        "email": "duplicate@example.com",
        "password": "Secure1234",
        "full_name": "Advocate One",
    }
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "logintest@example.com",
            "password": "Secure1234",
            "full_name": "Login Tester",
        },
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "logintest@example.com", "password": "Secure1234"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]["tokens"]


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrongpw@example.com",
            "password": "Secure1234",
            "full_name": "Wrong PW",
        },
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpw@example.com", "password": "WrongPass99"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "me@example.com",
            "password": "Secure1234",
            "full_name": "Me User",
        },
    )
    access_token = reg.json()["data"]["tokens"]["access_token"]

    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["email"] == "me@example.com"


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@example.com",
            "password": "Secure1234",
            "full_name": "Refresh User",
        },
    )
    refresh_token = reg.json()["data"]["tokens"]["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200
    new_tokens = response.json()["data"]
    assert "access_token" in new_tokens


@pytest.mark.asyncio
async def test_logout(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "logout@example.com",
            "password": "Secure1234",
            "full_name": "Logout User",
        },
    )
    refresh_token = reg.json()["data"]["tokens"]["refresh_token"]

    response = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": refresh_token}
    )
    assert response.status_code == 204

    # Token should now be revoked
    response2 = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert response2.status_code == 401