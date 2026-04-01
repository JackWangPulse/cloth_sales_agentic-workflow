"""Behavior tool for fetching and summarizing user behavior."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.agents.context import AgentContext
from app.services.behavior_cache_service import get_behavior_summary_cached_with_status

logger = logging.getLogger(__name__)


def summarize_behavior(logs: list) -> dict:
    """Legacy fallback behavior summarizer kept for error paths."""
    if not logs:
        return {
            "visit_count": 0,
            "max_stay_seconds": 0,
            "avg_stay_seconds": 0.0,
            "total_stay_seconds": 0,
            "has_enter_buy_page": False,
            "has_favorite": False,
            "has_share": False,
            "has_click_size_chart": False,
            "event_types": [],
            "event_type_counts": {},
        }
    return {"visit_count": len(logs)}


async def fetch_behavior_summary(
    context: AgentContext,
    db: Session,
    limit: int = 50,
    **kwargs: Any,
) -> AgentContext:
    """Load behavior summary into the shared agent context."""
    logger.info("=" * 80)
    logger.info("[BEHAVIOR_TOOL] Fetching behavior summary")
    logger.info(
        "[BEHAVIOR_TOOL] Context: user_id=%s, guide_id=%s, sku=%s, limit=%s",
        context.user_id,
        context.guide_id,
        context.sku,
        limit,
    )

    if not context.user_id or not context.guide_id or not context.sku:
        logger.warning(
            "[BEHAVIOR_TOOL] Missing user_id or guide_id or sku in context, returning empty summary"
        )
        context.behavior_summary = summarize_behavior([])
        return context

    try:
        summary, cache_status = await get_behavior_summary_cached_with_status(
            db=db,
            guide_id=context.guide_id,
            user_id=context.user_id,
            sku=context.sku,
            limit=limit,
        )
        context.behavior_summary = summary
        context.extra.setdefault("cache_diagnostics", {})[
            "behavior_summary"
        ] = cache_status

        logger.info(
            "[BEHAVIOR_TOOL] Summary created: visit_count=%s, max_stay=%ss, enter_buy_page=%s, cache=%s",
            summary["visit_count"],
            summary["max_stay_seconds"],
            summary["has_enter_buy_page"],
            cache_status,
        )
        logger.info("=" * 80)
        return context
    except Exception as exc:
        logger.error(
            "[BEHAVIOR_TOOL] Error fetching behavior summary: %s",
            exc,
            exc_info=True,
        )
        context.behavior_summary = summarize_behavior([])
        context.extra.setdefault("cache_diagnostics", {})["behavior_summary"] = (
            "error"
        )
        return context
