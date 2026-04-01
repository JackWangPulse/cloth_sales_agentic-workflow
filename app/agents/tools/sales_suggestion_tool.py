"""Tool for building sales suggestion pack from agent context."""
from __future__ import annotations

import logging

from app.agents.context import AgentContext
from app.services.graph_task_cache_service import (
    SUGGESTION_LOCK_TTL_SECONDS,
    acquire_lock,
    build_suggestion_cache_key,
    build_suggestion_lock_key,
    get_cached_suggestion,
    release_lock,
    set_cached_suggestion,
    wait_for_json_cache,
)
from app.services.sales_suggestion_service import build_suggestion_pack

logger = logging.getLogger(__name__)


async def build_sales_suggestion(context: AgentContext) -> AgentContext:
    """Build sales suggestion pack and store it back into context."""
    logger.info(
        "[SUGGESTION_TOOL] Building sales suggestion for sku=%s intent=%s",
        context.sku,
        context.intent_level,
    )

    cache_key = build_suggestion_cache_key(context)
    lock_key = build_suggestion_lock_key(context)
    lock_token = None

    cached_suggestion = get_cached_suggestion(context)
    if cached_suggestion:
        suggestion = cached_suggestion
    else:
        lock_token = acquire_lock(lock_key, SUGGESTION_LOCK_TTL_SECONDS)
        if lock_token is None:
            logger.info(
                "[SUGGESTION_TOOL] Lock busy for sku=%s user=%s, waiting for cache",
                context.sku,
                context.user_id,
            )
            waited_payload = wait_for_json_cache(cache_key)
            if isinstance(waited_payload, dict):
                suggestion = get_cached_suggestion(context)
                if suggestion is None:
                    suggestion = await build_suggestion_pack(context)
            else:
                logger.info(
                    "[SUGGESTION_TOOL] Cache wait timed out for sku=%s user=%s, continue without lock",
                    context.sku,
                    context.user_id,
                )
                suggestion = await build_suggestion_pack(context)
        else:
            try:
                suggestion = await build_suggestion_pack(context)
                set_cached_suggestion(context, suggestion)
            finally:
                release_lock(lock_key, lock_token)

    context.extra["sales_suggestion"] = suggestion
    context.extra["sales_suggestion_built"] = True

    if suggestion.message_pack:
        primary_message = next(
            (item.message for item in suggestion.message_pack if item.type == "primary"),
            suggestion.message_pack[0].message,
        )
        context.extra["final_message"] = primary_message

    return context
