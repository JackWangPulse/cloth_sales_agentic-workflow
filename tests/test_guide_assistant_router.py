"""Tests for guide assistant routing rules."""
from __future__ import annotations

from app.schemas.guide_assistant_schemas import GuideAssistantRequest, GuideRouteName
from app.services.guide_assistant_router import route_guide_request


def test_sales_graph_route_when_user_id_sku_and_guide_id_present():
    request = GuideAssistantRequest(
        query="this user stayed for a while, what should I send",
        user_id="user_001",
        sku="8WZ01CM1",
        guide_id="guide_001",
    )

    decision = route_guide_request(request)

    assert decision.route_name == GuideRouteName.SALES_GRAPH
    assert decision.normalized_params["user_id"] == "user_001"
    assert decision.normalized_params["sku"] == "8WZ01CM1"
    assert decision.normalized_params["guide_id"] == "guide_001"


def test_sales_graph_requires_guide_id():
    request = GuideAssistantRequest(
        query="this user stayed for a while, what should I send",
        user_id="user_001",
        sku="8WZ01CM1",
    )

    decision = route_guide_request(request)

    assert decision.route_name == GuideRouteName.UNKNOWN


def test_vector_search_route_for_search_intent_query():
    request = GuideAssistantRequest(
        query="help me find a few running shoes",
        guide_id="guide_001",
        top_k=5,
    )

    decision = route_guide_request(request)

    assert decision.route_name == GuideRouteName.VECTOR_SEARCH
    assert decision.normalized_params["query"] == "help me find a few running shoes"
    assert decision.normalized_params["top_k"] == 5


def test_unknown_route_when_inputs_do_not_match_supported_flow():
    request = GuideAssistantRequest(query="help me handle this")

    decision = route_guide_request(request)

    assert decision.route_name == GuideRouteName.UNKNOWN
