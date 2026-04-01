"""Sales graph API endpoints."""
from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.context import AgentContext
from app.agents.graph.sales_graph import BusinessLogicError, run_sales_graph
from app.agents.planner_agent import build_final_plan, plan_sales_flow
from app.core.database import get_db
from app.schemas.sales_graph_schemas import (
    FollowupPlaybookItemSchema,
    MessageItemSchema,
    SalesGraphRequest,
    SalesGraphResponse,
    SalesSuggestionSchema,
    SendRecommendationSchema,
)
from app.services.langsmith_service import trace_span
from app.services.sales_suggestion_service import (
    SalesSuggestion,
    build_suggestion_pack,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


def _to_sales_suggestion_schema(suggestion: SalesSuggestion) -> SalesSuggestionSchema:
    """Convert service suggestion object to API schema."""
    return SalesSuggestionSchema(
        intent_level=suggestion.intent_level,
        confidence=suggestion.confidence,
        why_now=suggestion.why_now,
        recommended_action=suggestion.recommended_action,
        action_explanation=suggestion.action_explanation,
        message_pack=[
            MessageItemSchema(
                type=item.type,
                strategy=item.strategy,
                message=item.message,
            )
            for item in suggestion.message_pack
        ],
        send_recommendation=SendRecommendationSchema(
            suggested=suggestion.send_recommendation.suggested,
            best_timing=suggestion.send_recommendation.best_timing,
            note=suggestion.send_recommendation.note,
            risk_level=suggestion.send_recommendation.risk_level,
            next_step=suggestion.send_recommendation.next_step,
        ),
        followup_playbook=[
            FollowupPlaybookItemSchema(
                condition=item.condition,
                reply=item.reply,
            )
            for item in suggestion.followup_playbook
        ],
    )


async def run_sales_graph_flow(
    *,
    user_id: str,
    sku: str,
    guide_id: str | None = None,
    use_custom_plan: bool = False,
) -> dict[str, Any]:
    """Run the sales graph flow and return plain response data."""
    logger.info("=" * 80)
    logger.info("[API] POST /ai/sales/graph - Request received")
    logger.info(
        "[API] Request: user_id=%s sku=%s guide_id=%s use_custom_plan=%s",
        user_id,
        sku,
        guide_id,
        use_custom_plan,
    )

    start_time = time.time()
    with trace_span(
        "sales_graph.flow",
        inputs={
            "user_id": user_id,
            "sku": sku,
            "guide_id": guide_id,
            "use_custom_plan": use_custom_plan,
        },
        tags=["sales_graph"],
    ) as trace:
        context = AgentContext(
            user_id=user_id,
            guide_id=guide_id,
            sku=sku,
            extra={"include_sales_suggestion": True},
        )

        initial_plan: list[str] | None = None
        if use_custom_plan:
            logger.info("[API] Generating custom plan using planner")
            initial_plan = await plan_sales_flow(context)
            logger.info("[API] Generated initial plan: %s", initial_plan)

            logger.info("[API] Building final plan with mandatory nodes enforcement")
            final_plan = build_final_plan(initial_plan, context)
            if final_plan != initial_plan:
                logger.info(
                    "[API] Plan updated: initial=%s final=%s",
                    initial_plan,
                    final_plan,
                )
        else:
            final_plan = None

        logger.info("[API] Executing sales graph...")
        result_context = await run_sales_graph(
            context,
            plan=final_plan,
            enforce_mandatory=True,
        )

        execution_time = time.time() - start_time
        rag_used = len(result_context.rag_chunks) > 0

        response_data: dict[str, Any] = {
            "user_id": result_context.user_id,
            "sku": result_context.sku,
            "intent_level": result_context.intent_level,
            "allowed": result_context.extra.get("allowed", False),
            "anti_disturb_blocked": result_context.extra.get("anti_disturb_blocked", False),
            "messages_count": len(result_context.messages),
            "rag_used": rag_used,
            "rag_chunks_count": len(result_context.rag_chunks),
            "rag_chunks": result_context.rag_chunks,
            "execution_time_seconds": round(execution_time, 3),
        }

        rag_diagnostics = result_context.extra.get("rag_diagnostics")
        response_data["rag_diagnostics"] = rag_diagnostics or {
            "retrieved_count": len(result_context.rag_chunks),
            "filtered_count": 0,
            "safe_count": len(result_context.rag_chunks),
            "filter_reasons": [],
        }

        response_data["plan_used"] = final_plan or [
            "fetch_product",
            "fetch_behavior_summary",
            "classify_intent",
            "anti_disturb_check",
            "retrieve_rag",
            "generate_copy",
            "build_sales_suggestion",
        ]

        response_data["decision_reason"] = _generate_decision_reason(
            intent_level=result_context.intent_level,
            allowed=result_context.extra.get("allowed", False),
            anti_disturb_blocked=result_context.extra.get("anti_disturb_blocked", False),
            context=result_context,
        )
        response_data["cache_diagnostics"] = result_context.extra.get(
            "cache_diagnostics",
            {},
        )

        if "intent_reason" in result_context.extra:
            response_data["intent_reason"] = result_context.extra["intent_reason"]

        if result_context.messages:
            last_message = result_context.messages[-1]
            if last_message.get("role") == "assistant":
                response_data["final_message"] = last_message.get("content", "")

        suggestion = result_context.extra.get("sales_suggestion")
        try:
            if suggestion is None and result_context.product and result_context.intent_level:
                logger.info("[API] Building sales suggestion pack in route fallback...")
                suggestion = await build_suggestion_pack(result_context)

            if suggestion is not None:
                response_data["sales_suggestion"] = _to_sales_suggestion_schema(
                    suggestion
                ).model_dump()
                if result_context.extra.get("final_message"):
                    response_data["final_message"] = result_context.extra["final_message"]
                elif suggestion.message_pack:
                    primary_message = next(
                        (item for item in suggestion.message_pack if item.type == "primary"),
                        suggestion.message_pack[0],
                    )
                    response_data["final_message"] = primary_message.message
        except Exception as exc:
            logger.error(
                "[API] Failed to build sales suggestion pack: %s",
                exc,
                exc_info=True,
            )

        if result_context.product:
            response_data["product_name"] = result_context.product.name
            response_data["product_price"] = float(result_context.product.price)

        logger.info(
            "[API] Sales graph executed successfully in %.3fs. intent=%s allowed=%s messages=%s rag_chunks=%s",
            execution_time,
            result_context.intent_level,
            result_context.extra.get("allowed"),
            len(result_context.messages),
            len(result_context.rag_chunks),
        )
        logger.info("=" * 80)
        trace.set_outputs(
            {
                "intent_level": result_context.intent_level,
                "allowed": result_context.extra.get("allowed"),
                "messages_count": len(result_context.messages),
                "rag_chunks_count": len(result_context.rag_chunks),
            }
        )
        return response_data


@router.post("/sales/graph", response_model=SalesGraphResponse)
async def execute_sales_graph(
    request: SalesGraphRequest,
    db: Session = Depends(get_db),
) -> SalesGraphResponse:
    """Execute the sales graph flow for guide-facing suggestion output."""
    del db

    logger.info("=" * 80)
    logger.info("[API] POST /ai/sales/graph - Request received")
    logger.info(
        "[API] Request: user_id=%s sku=%s guide_id=%s use_custom_plan=%s",
        request.user_id,
        request.sku,
        request.guide_id,
        request.use_custom_plan,
    )

    start_time = time.time()

    try:
        context = AgentContext(
            user_id=request.user_id,
            guide_id=request.guide_id,
            sku=request.sku,
            extra={"include_sales_suggestion": True},
        )

        initial_plan: list[str] | None = None
        if request.use_custom_plan:
            logger.info("[API] Generating custom plan using planner")
            initial_plan = await plan_sales_flow(context)
            logger.info("[API] Generated initial plan: %s", initial_plan)

            logger.info("[API] Building final plan with mandatory nodes enforcement")
            final_plan = build_final_plan(initial_plan, context)
            if final_plan != initial_plan:
                logger.info(
                    "[API] Plan updated: initial=%s final=%s",
                    initial_plan,
                    final_plan,
                )
        else:
            final_plan = None

        logger.info("[API] Executing sales graph...")
        result_context = await run_sales_graph(
            context,
            plan=final_plan,
            enforce_mandatory=True,
        )

        execution_time = time.time() - start_time
        rag_used = len(result_context.rag_chunks) > 0

        response_data: dict[str, Any] = {
            "user_id": result_context.user_id,
            "sku": result_context.sku,
            "intent_level": result_context.intent_level,
            "allowed": result_context.extra.get("allowed", False),
            "anti_disturb_blocked": result_context.extra.get(
                "anti_disturb_blocked",
                False,
            ),
            "messages_count": len(result_context.messages),
            "rag_used": rag_used,
            "rag_chunks_count": len(result_context.rag_chunks),
            "rag_chunks": result_context.rag_chunks,
            "execution_time_seconds": round(execution_time, 3),
        }

        rag_diagnostics = result_context.extra.get("rag_diagnostics")
        if rag_diagnostics:
            response_data["rag_diagnostics"] = rag_diagnostics
        else:
            response_data["rag_diagnostics"] = {
                "retrieved_count": len(result_context.rag_chunks),
                "filtered_count": 0,
                "safe_count": len(result_context.rag_chunks),
                "filter_reasons": [],
            }

        if final_plan:
            response_data["plan_used"] = final_plan
        else:
            response_data["plan_used"] = [
                "fetch_product",
                "fetch_behavior_summary",
                "classify_intent",
                "anti_disturb_check",
                "retrieve_rag",
                "generate_copy",
                "build_sales_suggestion",
            ]

        response_data["decision_reason"] = _generate_decision_reason(
            intent_level=result_context.intent_level,
            allowed=result_context.extra.get("allowed", False),
            anti_disturb_blocked=result_context.extra.get(
                "anti_disturb_blocked",
                False,
            ),
            context=result_context,
        )

        if "intent_reason" in result_context.extra:
            response_data["intent_reason"] = result_context.extra["intent_reason"]

        if result_context.messages:
            last_message = result_context.messages[-1]
            if last_message.get("role") == "assistant":
                response_data["final_message"] = last_message.get("content", "")

        suggestion = result_context.extra.get("sales_suggestion")
        try:
            if suggestion is None and result_context.product and result_context.intent_level:
                logger.info("[API] Building sales suggestion pack in route fallback...")
                suggestion = await build_suggestion_pack(result_context)

            if suggestion is not None:
                response_data["sales_suggestion"] = _to_sales_suggestion_schema(
                    suggestion
                ).model_dump()
                if result_context.extra.get("final_message"):
                    response_data["final_message"] = result_context.extra["final_message"]
                elif suggestion.message_pack:
                    primary_message = next(
                        (item for item in suggestion.message_pack if item.type == "primary"),
                        suggestion.message_pack[0],
                    )
                    response_data["final_message"] = primary_message.message
        except Exception as exc:
            logger.error(
                "[API] Failed to build sales suggestion pack: %s",
                exc,
                exc_info=True,
            )

        if result_context.product:
            response_data["product_name"] = result_context.product.name
            response_data["product_price"] = float(result_context.product.price)

        logger.info(
            "[API] Sales graph executed successfully in %.3fs. intent=%s allowed=%s messages=%s rag_chunks=%s",
            execution_time,
            result_context.intent_level,
            result_context.extra.get("allowed"),
            len(result_context.messages),
            len(result_context.rag_chunks),
        )
        logger.info("=" * 80)

        return SalesGraphResponse(
            success=True,
            message="Sales graph executed successfully",
            data=response_data,
        )

    except BusinessLogicError as exc:
        execution_time = time.time() - start_time
        logger.error(
            "[API] Business logic error after %.3fs: %s",
            execution_time,
            exc.message,
            exc_info=True,
        )
        logger.info("=" * 80)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Business logic validation failed",
                "error_code": exc.error_code,
                "message": exc.message,
            },
        ) from exc
    except Exception as exc:
        execution_time = time.time() - start_time
        logger.error(
            "[API] Sales graph execution failed after %.3fs: %s",
            execution_time,
            exc,
            exc_info=True,
        )
        logger.info("=" * 80)
        raise HTTPException(
            status_code=500,
            detail=f"Sales graph execution failed: {str(exc)}",
        ) from exc


def _generate_decision_reason(
    intent_level: str | None,
    allowed: bool,
    anti_disturb_blocked: bool,
    context: AgentContext,
) -> str:
    """Build a short human-readable decision reason."""
    reasons: list[str] = []

    if intent_level:
        intent_reason = context.extra.get("intent_reason", "")
        if intent_reason:
            reasons.append(f"用户意图={intent_level}，原因：{intent_reason}")
        else:
            reasons.append(f"用户意图={intent_level}")
    else:
        reasons.append("未能完成用户意图判断")

    if anti_disturb_blocked:
        reasons.append("反打扰规则阻止了主动发送")
    elif allowed:
        reasons.append("反打扰规则允许触达")
    else:
        reasons.append("反打扰结果未允许触达")

    return "；".join(reasons)


@router.get("/sales/graph/health")
async def sales_graph_health() -> dict[str, str]:
    """Health check for sales graph service."""
    try:
        from app.agents.graph.sales_graph import get_sales_graph

        graph = get_sales_graph()
        return {
            "status": "ok",
            "graph_compiled": "true" if graph is not None else "false",
            "message": "Sales graph service is healthy",
        }
    except Exception as exc:
        logger.error("[API] Sales graph health check failed: %s", exc, exc_info=True)
        return {
            "status": "error",
            "graph_compiled": "false",
            "message": f"Health check failed: {str(exc)}",
        }
