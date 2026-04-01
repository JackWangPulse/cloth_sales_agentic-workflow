"""Schemas for the unified guide assistant entrypoint."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class GuideRouteName(str, Enum):
    """Supported guide assistant route targets."""

    SALES_GRAPH = "sales_graph"
    VECTOR_SEARCH = "vector_search"
    UNKNOWN = "unknown"


class GuideAssistantRequest(BaseModel):
    """Request payload for the guide assistant entrypoint."""

    query: str = Field(..., min_length=1, description="Natural-language request from the guide")
    user_id: str | None = Field(None, description="Customer ID")
    sku: str | None = Field(None, description="Product SKU")
    guide_id: str | None = Field(None, description="Guide ID")
    top_k: int = Field(5, ge=1, le=20, description="Number of search results for vector search")
    use_custom_plan: bool = Field(
        False,
        description="Whether to use planner-generated plan for sales graph execution",
    )


class RouteDecision(BaseModel):
    """Route decision produced by the guide assistant router."""

    route_name: GuideRouteName
    reason: str
    normalized_params: dict[str, Any] = Field(default_factory=dict)


class GuideAssistantResponse(BaseModel):
    """Unified response payload for the guide assistant entrypoint."""

    route_name: GuideRouteName
    reason: str
    normalized_params: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    diagnostics: dict[str, Any] | None = None
