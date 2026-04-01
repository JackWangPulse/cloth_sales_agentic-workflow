"""Tests for guide assistant internal dispatch."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.guide_assistant_schemas import GuideRouteName, RouteDecision
from app.services.guide_assistant_service import execute_guide_request


@pytest.mark.asyncio
async def test_execute_sales_graph_dispatches_to_sales_graph():
    decision = RouteDecision(
        route_name=GuideRouteName.SALES_GRAPH,
        reason="sales flow",
        normalized_params={
            "user_id": "user_001",
            "sku": "8WZ01CM1",
            "guide_id": "guide_001",
            "use_custom_plan": True,
        },
    )

    with patch(
        "app.services.guide_assistant_service.execute_sales_graph_internal",
        new=AsyncMock(return_value={"intent_level": "high"}),
    ) as mocked:
        response = await execute_guide_request(decision)

    mocked.assert_awaited_once()
    assert response.route_name == GuideRouteName.SALES_GRAPH
    assert response.result == {"intent_level": "high"}
    assert response.diagnostics is not None
    assert response.diagnostics["route_name"] == "sales_graph"
    assert "total_duration_ms" in response.diagnostics


@pytest.mark.asyncio
async def test_execute_vector_search_dispatches_to_vector_search():
    decision = RouteDecision(
        route_name=GuideRouteName.VECTOR_SEARCH,
        reason="search flow",
        normalized_params={
            "query": "帮我找几款运动鞋",
            "top_k": 5,
        },
    )

    with patch(
        "app.services.guide_assistant_service.execute_vector_search_internal",
        new=AsyncMock(return_value={"total": 2}),
    ) as mocked:
        response = await execute_guide_request(decision)

    mocked.assert_awaited_once()
    assert response.route_name == GuideRouteName.VECTOR_SEARCH
    assert response.result == {"total": 2}
    assert response.diagnostics is not None
    assert response.diagnostics["route_name"] == "vector_search"


@pytest.mark.asyncio
async def test_execute_unknown_route_returns_empty_result():
    decision = RouteDecision(
        route_name=GuideRouteName.UNKNOWN,
        reason="unknown",
        normalized_params={"query": "帮我处理一下"},
    )

    response = await execute_guide_request(decision)

    assert response.route_name == GuideRouteName.UNKNOWN
    assert response.result is None
