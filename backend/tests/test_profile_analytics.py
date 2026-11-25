from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_profile_get_update_persists(client):
    get_response = await client.get("/v1/profile")
    assert get_response.status_code == 200

    update_response = await client.put(
        "/v1/profile",
        json={
            "full_name": "Ananth Test",
            "email": "ananth@example.com",
            "role": "Security Analyst",
            "organization": "government",
            "phone": "+91-1234567890",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["full_name"] == "Ananth Test"

    persisted = await client.get("/v1/profile")
    assert persisted.status_code == 200
    assert persisted.json()["email"] == "ananth@example.com"
    assert persisted.json()["organization"] == "government"


@pytest.mark.asyncio
async def test_analytics_period_endpoint(client):
    response = await client.get(
        "/v1/analytics",
        params={"days": 7, "organization": "enterprise"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["days"] == 7
    assert data["total"] >= 0
    assert isinstance(data["trend"], list)
