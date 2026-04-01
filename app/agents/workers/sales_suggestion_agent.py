"""Worker node for building sales suggestion pack."""
from __future__ import annotations

import logging

from app.agents.context import AgentContext
from app.agents.tools.sales_suggestion_tool import build_sales_suggestion

logger = logging.getLogger(__name__)


async def build_sales_suggestion_node(context: AgentContext) -> AgentContext:
    """Build sales suggestion pack as a graph node."""
    logger.info("=" * 80)
    logger.info("[SUGGESTION_AGENT] Building sales suggestion pack")
    logger.info(
        "[SUGGESTION_AGENT] Context: sku=%s has_product=%s intent=%s allowed=%s",
        context.sku,
        context.product is not None,
        context.intent_level,
        context.extra.get("allowed"),
    )

    try:
        context = await build_sales_suggestion(context)
        logger.info("[SUGGESTION_AGENT] Suggestion pack built successfully")
        logger.info("=" * 80)
        return context
    except Exception as exc:
        logger.error(
            "[SUGGESTION_AGENT] Failed to build sales suggestion pack: %s",
            exc,
            exc_info=True,
        )
        return context
