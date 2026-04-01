"""LangGraph-based sales flow state machine."""
from __future__ import annotations

import logging
from typing import Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.context import AgentContext
from app.agents.planner_agent import (
    TASK_ANTI_DISTURB_CHECK,
    TASK_BUILD_SALES_SUGGESTION,
    TASK_CLASSIFY_INTENT,
    TASK_FETCH_BEHAVIOR_SUMMARY,
    TASK_FETCH_PRODUCT,
    TASK_GENERATE_COPY,
    TASK_RETRIEVE_RAG,
    build_final_plan,
)
from app.agents.tools.behavior_tool import fetch_behavior_summary
from app.agents.tools.product_tool import fetch_product
from app.agents.tools.rag_tool import retrieve_rag
from app.agents.workers.copy_agent import generate_copy_node
from app.agents.workers.intent_agent import classify_intent_node
from app.agents.workers.sales_agent import anti_disturb_check_node
from app.agents.workers.sales_suggestion_agent import build_sales_suggestion_node
from app.core.database import SessionLocal
from app.services.langsmith_service import trace_span

logger = logging.getLogger(__name__)


class GraphState(TypedDict):
    """LangGraph state wrapper."""

    context: AgentContext


def _trace_node_inputs(context: AgentContext, node_name: str) -> dict:
    """Build lightweight LangSmith inputs for a graph node."""
    return {
        "node_name": node_name,
        "user_id": context.user_id,
        "guide_id": context.guide_id,
        "sku": context.sku,
        "intent_level": context.intent_level,
        "has_product": context.product is not None,
        "has_behavior_summary": context.behavior_summary is not None,
        "messages_count": len(context.messages),
        "rag_chunks_count": len(context.rag_chunks),
    }


def _trace_node_outputs(context: AgentContext) -> dict:
    """Build lightweight LangSmith outputs for a graph node."""
    return {
        "intent_level": context.intent_level,
        "allowed": context.extra.get("allowed"),
        "anti_disturb_blocked": context.extra.get("anti_disturb_blocked"),
        "has_product": context.product is not None,
        "has_behavior_summary": context.behavior_summary is not None,
        "messages_count": len(context.messages),
        "rag_chunks_count": len(context.rag_chunks),
    }


def _create_node_wrapper(node_func, node_name: str, requires_db: bool = False):
    """Wrap node function for LangGraph state shape."""

    async def wrapper(state: GraphState) -> GraphState:
        context = state["context"]
        try:
            with trace_span(
                f"sales_graph.node.{node_name}",
                run_type="chain",
                inputs=_trace_node_inputs(context, node_name),
                tags=["sales_graph", "node", node_name],
                metadata={"node_name": node_name, "requires_db": requires_db},
            ) as trace:
                if requires_db:
                    db = SessionLocal()
                    try:
                        context = await node_func(context, db)
                    finally:
                        db.close()
                else:
                    context = await node_func(context)
                trace.set_outputs(_trace_node_outputs(context))
            return {"context": context}
        except Exception as exc:
            logger.error(
                "[SALES_GRAPH] Node %s failed: %s",
                node_name,
                exc,
                exc_info=True,
            )
            return state

    return wrapper


def _should_build_sales_suggestion(context: AgentContext) -> bool:
    """Whether current route expects graph-level suggestion output."""
    return bool(context.extra.get("include_sales_suggestion", False))


def _should_continue(
    state: GraphState,
) -> Literal["retrieve_rag", "generate_copy", "build_sales_suggestion", END]:
    """Route after anti-disturb check."""
    context = state["context"]
    allowed = context.extra.get("allowed", False)
    intent_level = context.intent_level

    logger.info(
        "[SALES_GRAPH] Routing decision: allowed=%s intent_level=%s",
        allowed,
        intent_level,
    )

    if not allowed:
        if _should_build_sales_suggestion(context):
            logger.info(
                "[SALES_GRAPH] Anti-disturb blocked send, routing to build_sales_suggestion"
            )
            return "build_sales_suggestion"
        logger.info("[SALES_GRAPH] Anti-disturb blocked send, ending early")
        return END

    if intent_level == "low":
        logger.info("[SALES_GRAPH] Low intent detected, skipping RAG")
        return "generate_copy"

    logger.info("[SALES_GRAPH] RAG disabled, routing directly to generate_copy")
    return "generate_copy"


def _route_after_generate_copy(
    state: GraphState,
) -> Literal["build_sales_suggestion", END]:
    """Route after copy generation."""
    if _should_build_sales_suggestion(state["context"]):
        return "build_sales_suggestion"
    return END


def _create_sales_graph():
    """Create compiled sales graph."""
    graph = StateGraph(GraphState)

    graph.add_node(
        TASK_FETCH_PRODUCT,
        _create_node_wrapper(fetch_product, TASK_FETCH_PRODUCT, requires_db=True),
    )
    graph.add_node(
        TASK_FETCH_BEHAVIOR_SUMMARY,
        _create_node_wrapper(
            fetch_behavior_summary,
            TASK_FETCH_BEHAVIOR_SUMMARY,
            requires_db=True,
        ),
    )
    graph.add_node(
        TASK_CLASSIFY_INTENT,
        _create_node_wrapper(classify_intent_node, TASK_CLASSIFY_INTENT),
    )
    graph.add_node(
        TASK_ANTI_DISTURB_CHECK,
        _create_node_wrapper(anti_disturb_check_node, TASK_ANTI_DISTURB_CHECK),
    )
    graph.add_node(
        TASK_RETRIEVE_RAG,
        _create_node_wrapper(retrieve_rag, TASK_RETRIEVE_RAG),
    )
    graph.add_node(
        TASK_GENERATE_COPY,
        _create_node_wrapper(generate_copy_node, TASK_GENERATE_COPY),
    )
    graph.add_node(
        TASK_BUILD_SALES_SUGGESTION,
        _create_node_wrapper(
            build_sales_suggestion_node,
            TASK_BUILD_SALES_SUGGESTION,
        ),
    )

    graph.set_entry_point(TASK_FETCH_PRODUCT)
    graph.add_edge(TASK_FETCH_PRODUCT, TASK_FETCH_BEHAVIOR_SUMMARY)
    graph.add_edge(TASK_FETCH_BEHAVIOR_SUMMARY, TASK_CLASSIFY_INTENT)
    graph.add_edge(TASK_CLASSIFY_INTENT, TASK_ANTI_DISTURB_CHECK)
    graph.add_conditional_edges(
        TASK_ANTI_DISTURB_CHECK,
        _should_continue,
        {
            # TASK_RETRIEVE_RAG: TASK_RETRIEVE_RAG,
            TASK_GENERATE_COPY: TASK_GENERATE_COPY,
            TASK_BUILD_SALES_SUGGESTION: TASK_BUILD_SALES_SUGGESTION,
            END: END,
        },
    )
    # graph.add_edge(TASK_RETRIEVE_RAG, TASK_GENERATE_COPY)
    graph.add_conditional_edges(
        TASK_GENERATE_COPY,
        _route_after_generate_copy,
        {
            TASK_BUILD_SALES_SUGGESTION: TASK_BUILD_SALES_SUGGESTION,
            END: END,
        },
    )
    graph.add_edge(TASK_BUILD_SALES_SUGGESTION, END)

    compiled_graph = graph.compile()
    logger.info("[SALES_GRAPH] Sales graph created and compiled successfully")
    return compiled_graph


_sales_graph = None


def get_sales_graph():
    """Get singleton compiled sales graph."""
    global _sales_graph
    if _sales_graph is None:
        _sales_graph = _create_sales_graph()
    return _sales_graph


class BusinessLogicError(Exception):
    """Raised when required business fields are missing after graph execution."""

    def __init__(self, message: str, error_code: str = "MISSING_MANDATORY_FIELD"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


async def run_sales_graph(
    context: AgentContext,
    plan: list[str] | None = None,
    enforce_mandatory: bool = True,
) -> AgentContext:
    """Run graph flow or explicit plan."""
    logger.info("=" * 80)
    logger.info("[SALES_GRAPH] Starting sales graph execution")
    logger.info(
        "[SALES_GRAPH] Context: user_id=%s sku=%s",
        context.user_id,
        context.sku,
    )

    final_plan = plan
    if plan and enforce_mandatory:
        logger.info("[SALES_GRAPH] Enforcing mandatory nodes in plan")
        final_plan = build_final_plan(plan, context)
        if final_plan != plan:
            logger.info(
                "[SALES_GRAPH] Plan updated: original=%s final=%s",
                plan,
                final_plan,
            )

    if final_plan:
        logger.info("[SALES_GRAPH] Using plan: %s", " -> ".join(final_plan))
        result_context = await _execute_plan(context, final_plan)
    else:
        logger.info("[SALES_GRAPH] Using full graph flow")
        graph = get_sales_graph()
        initial_state: GraphState = {"context": context}
        try:
            final_state = await graph.ainvoke(initial_state)
            result_context = final_state["context"]
        except Exception as exc:
            logger.error(
                "[SALES_GRAPH] Graph execution failed: %s",
                exc,
                exc_info=True,
            )
            logger.info("=" * 80)
            return context

    _validate_mandatory_fields(result_context, final_plan)

    logger.info(
        "[SALES_GRAPH] Graph execution completed: messages=%s intent_level=%s allowed=%s",
        len(result_context.messages),
        result_context.intent_level,
        result_context.extra.get("allowed"),
    )
    logger.info("=" * 80)
    return result_context


def _validate_mandatory_fields(context: AgentContext, plan: list[str] | None) -> None:
    """Validate business-critical fields after execution."""
    if context.user_id and context.behavior_summary and context.intent_level is None:
        plan_str = " -> ".join(plan) if plan else "full_graph_flow"
        error_msg = (
            "Mandatory field 'intent_level' is missing after graph execution. "
            "This indicates that 'classify_intent' node was not executed or failed. "
            f"Plan executed: {plan_str}. "
            "This is a business logic error and must be fixed."
        )
        logger.error("[SALES_GRAPH] %s", error_msg)
        raise BusinessLogicError(error_msg, error_code="MISSING_INTENT_LEVEL")

    if (context.intent_level is not None or context.behavior_summary is not None) and (
        "allowed" not in context.extra
    ):
        plan_str = " -> ".join(plan) if plan else "full_graph_flow"
        error_msg = (
            "Mandatory field 'allowed' is missing after graph execution. "
            "This indicates that 'anti_disturb_check' node was not executed or failed. "
            f"Plan executed: {plan_str}. "
            "This is a business logic error and must be fixed."
        )
        logger.error("[SALES_GRAPH] %s", error_msg)
        raise BusinessLogicError(error_msg, error_code="MISSING_ANTI_DISTURB_RESULT")


async def _execute_plan(context: AgentContext, plan: list[str]) -> AgentContext:
    """Execute explicit node plan in order."""
    logger.info("[SALES_GRAPH] Executing custom plan with %s nodes", len(plan))

    current_context = context
    anti_disturb_blocked = False

    for idx, node_name in enumerate(plan, 1):
        logger.info("[SALES_GRAPH] Step %s/%s: %s", idx, len(plan), node_name)

        try:
            if anti_disturb_blocked and node_name != TASK_BUILD_SALES_SUGGESTION:
                logger.info(
                    "[SALES_GRAPH] Skipping %s because anti-disturb already blocked send",
                    node_name,
                )
                continue

            with trace_span(
                f"sales_graph.node.{node_name}",
                run_type="chain",
                inputs=_trace_node_inputs(current_context, node_name),
                tags=["sales_graph", "node", node_name],
                metadata={"node_name": node_name, "execution_mode": "explicit_plan"},
            ) as trace:
                if node_name == TASK_FETCH_PRODUCT:
                    db = SessionLocal()
                    try:
                        current_context = await fetch_product(current_context, db)
                    finally:
                        db.close()

                elif node_name == TASK_FETCH_BEHAVIOR_SUMMARY:
                    db = SessionLocal()
                    try:
                        current_context = await fetch_behavior_summary(current_context, db)
                    finally:
                        db.close()

                elif node_name == TASK_CLASSIFY_INTENT:
                    current_context = await classify_intent_node(current_context)

                elif node_name == TASK_ANTI_DISTURB_CHECK:
                    current_context = await anti_disturb_check_node(current_context)
                    allowed = current_context.extra.get("allowed", False)
                    if not allowed:
                        if TASK_BUILD_SALES_SUGGESTION in plan[idx:]:
                            logger.info(
                                "[SALES_GRAPH] Anti-disturb denied, keeping only build_sales_suggestion for remaining plan"
                            )
                            anti_disturb_blocked = True
                        else:
                            logger.info(
                                "[SALES_GRAPH] Anti-disturb denied, ending plan execution early"
                            )
                            trace.set_outputs(_trace_node_outputs(current_context))
                            break

                elif node_name == TASK_RETRIEVE_RAG:
                    logger.info("[SALES_GRAPH] Skipping retrieve_rag because RAG is disabled")
                    continue

                elif node_name == TASK_GENERATE_COPY:
                    current_context = await generate_copy_node(current_context)

                elif node_name == TASK_BUILD_SALES_SUGGESTION:
                    current_context = await build_sales_suggestion_node(current_context)

                else:
                    logger.warning("[SALES_GRAPH] Unknown node: %s, skipping", node_name)
                    continue

                trace.set_outputs(_trace_node_outputs(current_context))

        except Exception as exc:
            logger.error(
                "[SALES_GRAPH] Node %s failed: %s",
                node_name,
                exc,
                exc_info=True,
            )
            continue

    logger.info("[SALES_GRAPH] Plan execution completed")
    return current_context
