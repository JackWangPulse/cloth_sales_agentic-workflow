"""Rule-based router for the unified guide assistant entrypoint."""

from __future__ import annotations

from app.schemas.guide_assistant_schemas import (
    GuideAssistantRequest,
    GuideRouteName,
    RouteDecision,
)

SEARCH_KEYWORDS = (
    "找衣服",
    "找几款",
    "推荐几款",
    "推荐衣服",
    "上衣",
    "下装",
    "裤子",
    "裙子",
    "连衣裙",
    "衬衫",
    "卫衣",
    "针织衫",
    "毛衣",
    "外套",
    "夹克",
    "羽绒服",
    "牛仔裤",
    "西装裤",
    "通勤穿搭",
    "日常穿搭",
    "搭配",
    "衣服",
)


def route_guide_request(request: GuideAssistantRequest) -> RouteDecision:
    """Choose the downstream capability for a guide request."""
    normalized_query = request.query.strip()

    if request.user_id and request.sku and request.guide_id:
        return RouteDecision(
            route_name=GuideRouteName.SALES_GRAPH,
            reason="检测到 user_id、sku 和 guide_id，走导购跟进建议链路。",
            normalized_params={
                "query": normalized_query,
                "user_id": request.user_id,
                "sku": request.sku,
                "guide_id": request.guide_id,
                "use_custom_plan": request.use_custom_plan,
            },
        )

    if any(keyword in normalized_query for keyword in SEARCH_KEYWORDS):
        return RouteDecision(
            route_name=GuideRouteName.VECTOR_SEARCH,
            reason="检测到找款/搜款意图，走商品搜索链路。",
            normalized_params={
                "query": normalized_query,
                "guide_id": request.guide_id,
                "top_k": request.top_k,
            },
        )

    return RouteDecision(
        route_name=GuideRouteName.UNKNOWN,
        reason="当前输入无法判断支持的路由。sales_graph 需要同时提供 user_id、sku 和 guide_id。",
        normalized_params={
            "query": normalized_query,
            "user_id": request.user_id,
            "sku": request.sku,
            "guide_id": request.guide_id,
            "top_k": request.top_k,
            "use_custom_plan": request.use_custom_plan,
        },
    )
