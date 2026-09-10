"""
Matter endpoint tests.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _register_and_token(client: AsyncClient, email: str) -> str:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Secure1234", "full_name": "Test Lawyer"},
    )
    return reg.json()["data"]["tokens"]["access_token"]


@pytest.mark.asyncio
async def test_create_matter(client: AsyncClient) -> None:
    token = await _register_and_token(client, "matteruser1@example.com")
    response = await client.post(
        "/api/v1/matters",
        json={"title": "My First Case", "matter_type": "civil"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["data"]["title"] == "My First Case"
    assert data["data"]["status"] == "active"


@pytest.mark.asyncio
async def test_list_matters(client: AsyncClient) -> None:
    token = await _register_and_token(client, "matteruser2@example.com")
    await client.post(
        "/api/v1/matters",
        json={"title": "Case A"},
        headers={"Authorization": f"Bearer {token}"},
    )
    await client.post(
        "/api/v1/matters",
        json={"title": "Case B"},
        headers={"Authorization": f"Bearer {token}"},
    )
    response = await client.get(
        "/api/v1/matters", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["total"] >= 2


@pytest.mark.asyncio
async def test_matter_isolation(client: AsyncClient) -> None:
    """User A should not see User B's matters."""
    token_a = await _register_and_token(client, "isolationa@example.com")
    token_b = await _register_and_token(client, "isolationb@example.com")

    create_resp = await client.post(
        "/api/v1/matters",
        json={"title": "User A Secret Case"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    matter_id = create_resp.json()["data"]["id"]

    # User B tries to access User A's matter
    response = await client.get(
        f"/api/v1/matters/{matter_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 403