"""
Tests for §75.1 rate limiting and the v2.2 guest research flow.

Rate limiting is disabled by conftest for the main suite; these tests
re-enable it and use unique per-run IPs (X-Forwarded-For) so shared Redis
counters from dev/E2E runs cannot pollute assertions.
"""

from __future__ import annotations

import uuid

import pytest

from app.core.config import settings
from app.common import rate_limit as rl


@pytest.fixture(autouse=True)
def _enable_rate_limiting():
    old = settings.RATE_LIMITING_ENABLED
    settings.RATE_LIMITING_ENABLED = True
    # Force the deterministic in-memory fallback so tests never depend on the
    # shared Redis instance's state.
    rl._local_buckets.clear()
    import app.common.rate_limit as rl_mod

    original_check = rl_mod.check_rate_limit

    async def memory_only_check(name: str, identity: str) -> None:
        if not settings.RATE_LIMITING_ENABLED or name not in rl_mod.RATE_LIMITS:
            return
        limit, window = rl_mod.RATE_LIMITS[name]
        if not rl_mod._memory_hit(f"rl:{name}:{identity}", limit, window):
            from app.core.exceptions import RateLimitError

            raise RateLimitError(
                message="Rate limit exceeded. Please try again later.",
                details={"limit": limit, "window_seconds": window},
            )

    rl_mod.check_rate_limit = memory_only_check
    yield
    rl_mod.check_rate_limit = original_check
    settings.RATE_LIMITING_ENABLED = old
    rl._local_buckets.clear()


def _ip() -> str:
    return f"10.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"


@pytest.mark.asyncio
async def test_guest_search_limit_two_per_day(client):
    ip = _ip()
    headers = {"X-Forwarded-For": ip}
    body = {"query": "Bail under Article 21 after three years of custody without trial."}

    r1 = await client.post("/api/v1/research/query", json=body, headers=headers)
    assert r1.status_code == 202, r1.text
    data1 = r1.json()
    assert data1["guest_searches_remaining"] == 1
    assert data1["session_id"]

    r2 = await client.post("/api/v1/research/query", json=body, headers=headers)
    assert r2.status_code == 202, r2.text
    assert r2.json()["guest_searches_remaining"] == 0

    r3 = await client.post("/api/v1/research/query", json=body, headers=headers)
    assert r3.status_code == 429
    assert r3.json()["error"]["code"] == "RATE_LIMITED"


@pytest.mark.asyncio
async def test_guest_session_status_readable_by_creator_ip(client):
    ip = _ip()
    headers = {"X-Forwarded-For": ip}
    body = {"query": "Dowry death presumption under Section 113B Evidence Act."}

    r = await client.post("/api/v1/research/query", json=body, headers=headers)
    sid = r.json()["session_id"]

    status = await client.get(f"/api/v1/research/{sid}", headers=headers)
    assert status.status_code == 200
    assert status.json()["created_by"] is None  # guest session

    # A different IP must not read someone else's guest session.
    other = await client.get(f"/api/v1/research/{sid}", headers={"X-Forwarded-For": _ip()})
    assert other.status_code == 404


@pytest.mark.asyncio
async def test_otp_forgot_password_one_per_minute(client):
    ip = _ip()
    headers = {"X-Forwarded-For": ip}

    r1 = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "otp@example.com"}, headers=headers
    )
    assert r1.status_code == 204

    r2 = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "otp@example.com"}, headers=headers
    )
    assert r2.status_code == 429

    # A different IP is not affected (per-IP+window isolation).
    r3 = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "otp@example.com"},
        headers={"X-Forwarded-For": _ip()},
    )
    assert r3.status_code == 204


@pytest.mark.asyncio
async def test_login_brute_force_limit(client):
    ip = _ip()
    headers = {"X-Forwarded-For": ip}
    payload = {"email": "bruteforce@example.com", "password": "WrongPass123"}

    codes = []
    for _ in range(11):
        r = await client.post("/api/v1/auth/login", json=payload, headers=headers)
        codes.append(r.status_code)
    assert codes[:10] == [401] * 10  # normal invalid-credential responses
    assert codes[10] == 429  # 11th attempt within 5 minutes is blocked


@pytest.mark.asyncio
async def test_register_limit_per_ip(client):
    ip = _ip()
    headers = {"X-Forwarded-For": ip}

    codes = []
    for i in range(6):
        r = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"reg_{uuid.uuid4().hex[:8]}@example.com",
                "password": "Secure1234",
                "full_name": "RL Test",
            },
            headers=headers,
        )
        codes.append(r.status_code)
    assert codes[:5] == [201] * 5
    assert codes[5] == 429
