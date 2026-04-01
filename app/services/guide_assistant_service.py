"""Execution service for the unified guide assistant entrypoint."""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

from app.services.langsmith_service import trace_span
from app.services.llm_client import get_llm_duration_ms, reset_llm_timing
from app.schemas.guide_assistant_schemas import (
    GuideAssistantResponse,
    GuideRouteName,
    RouteDecision,
)

logger = logging.getLogger(__name__)

SKU_PATTERN = re.compile(r"\[SKU:([^\]]+)\]|SKU[：:]\s*([A-Z0-9]+)", re.IGNORECASE)


def _extract_sku_from_chunk(chunk: str) -> str | None:
    """Extract SKU from a retrieved chunk."""
    match = SKU_PATTERN.search(chunk)
    if not match:
        return None
    return (match.group(1) or match.group(2) or "").upper() or None


async def _generate_copy_candidates_for_product(product: Any) -> list[dict[str, Any]]:
    """Generate copy candidates for a single product."""
    from app.services.product_copy_service import generate_product_copy
    from app.services.product_copy_cache_service import (
        get_cached_product_copy_candidates,
        set_cached_product_copy_candidates,
    )

    scene = "guide_chat"
    style = "natural"
    max_length = 50
    sku = getattr(product, "sku", None)
    if sku:
        cached_candidates = get_cached_product_copy_candidates(
            sku=sku,
            scene=scene,
            style=style,
            max_length=max_length,
        )
        if cached_candidates is not None:
            return cached_candidates

    with trace_span(
        "guide_assistant.product_copy_item",
        inputs={
            "sku": sku,
            "scene": scene,
            "style": style,
            "max_length": max_length,
        },
        metadata={"product_name": getattr(product, "name", None)},
        tags=["guide_assistant", "product_copy"],
    ) as trace:
        candidates = await generate_product_copy(
            product=product,
            scene=scene,
            style=style,
            max_length=max_length,
        )
        trace.set_outputs(
            {
                "sku": sku,
                "candidate_count": len(candidates),
            }
        )
    serialized_candidates = [
        {
            "scene": candidate.scene,
            "style": candidate.style,
            "message": candidate.message,
        }
        for candidate in candidates
    ]
    if sku:
        set_cached_product_copy_candidates(
            sku=sku,
            scene=scene,
            style=style,
            max_length=max_length,
            copy_candidates=serialized_candidates,
        )
    return serialized_candidates


async def execute_vector_search_internal(
    *,
    query: str,
    top_k: int,
) -> dict[str, Any]:
    """Execute a minimal vector search without going through HTTP."""
    from app.api.v1.vector_search import get_vector_store
    from app.core.database import SessionLocal
    from app.repositories.product_repository import get_product_by_sku

    start_time = time.perf_counter()
    with trace_span(
        "guide_assistant.vector_search_flow",
        inputs={"query": query, "top_k": top_k},
        tags=["guide_assistant", "vector_search"],
    ) as trace:
        vector_store = get_vector_store()
        if vector_store.index is None or not vector_store.chunks:
            raise RuntimeError("Vector store is not initialized")

        search_results = await vector_store.search_async(query, top_k=top_k)
        results = []
        copy_tasks: list[tuple[int, str, asyncio.Task[list[dict[str, Any]]]]] = []
        db = SessionLocal()
        try:
            for index, (chunk, score) in enumerate(search_results[:top_k]):
                item: dict[str, Any] = {
                    "chunk": chunk,
                    "score": round(score, 4),
                    "rank": index + 1,
                }

                sku = _extract_sku_from_chunk(chunk)
                if sku:
                    item["sku"] = sku

                if sku and index < 3:
                    product = get_product_by_sku(db, sku)
                    if product:
                        item["product_name"] = product.name
                        item["copy_candidates"] = []
                        copy_tasks.append(
                            (
                                index,
                                sku,
                                asyncio.create_task(
                                    _generate_copy_candidates_for_product(product)
                                ),
                            )
                        )

                results.append(item)

            if copy_tasks:
                task_results = await asyncio.gather(
                    *(task for _, _, task in copy_tasks),
                    return_exceptions=True,
                )
                for (index, sku, _), task_result in zip(copy_tasks, task_results):
                    if isinstance(task_result, Exception):
                        logger.warning(
                            "[GUIDE_ASSISTANT] Product copy generation failed for sku=%s: %s",
                            sku,
                            task_result,
                        )
                        results[index]["copy_candidates"] = []
                    else:
                        results[index]["copy_candidates"] = task_result
        finally:
            db.close()

        output = {
            "query": query,
            "results": results,
            "total": len(results),
            "diagnostics": {
                "downstream_duration_ms": round(
                    (time.perf_counter() - start_time) * 1000,
                    2,
                ),
                "cache_diagnostics": {"vector_search": "not_applicable"},
            },
        }
        trace.set_outputs(
            {
                "total": len(results),
                "copy_enriched_count": sum(
                    1 for item in results if item.get("copy_candidates")
                ),
            }
        )
        return output


async def execute_sales_graph_internal(
    *,
    user_id: str,
    sku: str,
    guide_id: str | None,
    use_custom_plan: bool,
) -> dict[str, Any]:
    """Execute the sales graph without routing through HTTP."""
    from app.api.v1.sales_graph import run_sales_graph_flow

    start_time = time.perf_counter()
    with trace_span(
        "guide_assistant.sales_graph_flow",
        inputs={
            "user_id": user_id,
            "sku": sku,
            "guide_id": guide_id,
            "use_custom_plan": use_custom_plan,
        },
        tags=["guide_assistant", "sales_graph"],
    ) as trace:
        result = await run_sales_graph_flow(
            user_id=user_id,
            sku=sku,
            guide_id=guide_id,
            use_custom_plan=use_custom_plan,
        )
        result["diagnostics"] = {
            "downstream_duration_ms": round((time.perf_counter() - start_time) * 1000, 2),
            "cache_diagnostics": result.get("cache_diagnostics", {}),
        }
        trace.set_outputs(
            {
                "intent_level": result.get("intent_level"),
                "allowed": result.get("allowed"),
                "rag_used": result.get("rag_used"),
            }
        )
        return result


async def execute_guide_request(decision: RouteDecision) -> GuideAssistantResponse:
    """Dispatch a routed guide request to its downstream capability."""
    result: dict[str, Any] | None
    start_time = time.perf_counter()
    reset_llm_timing()

    with trace_span(
        "guide_assistant.request",
        inputs={
            "route_name": decision.route_name.value,
            "reason": decision.reason,
            "normalized_params": decision.normalized_params,
        },
        metadata={"route_name": decision.route_name.value},
        tags=["guide_assistant"],
    ) as trace:
        if decision.route_name == GuideRouteName.VECTOR_SEARCH:
            result = await execute_vector_search_internal(
                query=str(decision.normalized_params["query"]),
                top_k=int(decision.normalized_params.get("top_k", 5)),
            )
        elif decision.route_name == GuideRouteName.SALES_GRAPH:
            result = await execute_sales_graph_internal(
                user_id=str(decision.normalized_params["user_id"]),
                sku=str(decision.normalized_params["sku"]),
                guide_id=decision.normalized_params.get("guide_id"),
                use_custom_plan=bool(
                    decision.normalized_params.get("use_custom_plan", False)
                ),
            )
        else:
            result = None

        result_diagnostics = result.get("diagnostics", {}) if isinstance(result, dict) else {}
        total_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        llm_duration_ms = round(get_llm_duration_ms(), 2)
        non_llm_duration_ms = round(max(total_duration_ms - llm_duration_ms, 0.0), 2)
        cache_diagnostics = result_diagnostics.get("cache_diagnostics", {})

        logger.info(
            "[GUIDE_ASSISTANT] route=%s total_ms=%.2f llm_ms=%.2f non_llm_ms=%.2f downstream_ms=%s cache=%s",
            decision.route_name.value,
            total_duration_ms,
            llm_duration_ms,
            non_llm_duration_ms,
            result_diagnostics.get("downstream_duration_ms"),
            cache_diagnostics,
        )

        response = GuideAssistantResponse(
            route_name=decision.route_name,
            reason=decision.reason,
            normalized_params=decision.normalized_params,
            result=result,
            diagnostics={
                "route_name": decision.route_name.value,
                "total_duration_ms": total_duration_ms,
                "llm_duration_ms": llm_duration_ms,
                "non_llm_duration_ms": non_llm_duration_ms,
                "downstream_duration_ms": result_diagnostics.get("downstream_duration_ms"),
                "cache_diagnostics": cache_diagnostics,
            },
        )
        trace.set_outputs(
            {
                "route_name": decision.route_name.value,
                "total_duration_ms": total_duration_ms,
                "llm_duration_ms": llm_duration_ms,
                "non_llm_duration_ms": non_llm_duration_ms,
            }
        )
        return response
