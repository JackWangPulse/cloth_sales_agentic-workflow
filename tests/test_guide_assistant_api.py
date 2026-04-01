"""Tests for the unified guide assistant API."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


def test_guide_assistant_returns_route_name_and_result():
    client = TestClient(app)

    with patch(
        "app.api.v1.guide_assistant.execute_guide_request",
        new=AsyncMock(
            return_value={
                "route_name": "vector_search",
                "reason": "Detected product search intent from query.",
                "normalized_params": {"query": "帮我找几款运动鞋", "top_k": 5},
                "result": {"total": 1},
            }
        ),
    ):
        response = client.post(
            "/ai/guide/assistant",
            json={
                "query": "帮我找几款运动鞋",
                "guide_id": "guide_001",
            },
        )

    assert response.status_code == 200
    assert response.json()["data"]["route_name"] == "vector_search"
