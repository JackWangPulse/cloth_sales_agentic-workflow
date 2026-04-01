"""Redis-backed cache and distributed lock helpers for graph-heavy tasks."""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict
from typing import Any

from app.agents.context import AgentContext
from app.services.cache_service import get_cache_client, get_json, set_json
from app.services.sales_suggestion_service import (
    FollowupPlaybookItem,
    MessageItem,
    SalesSuggestion,
    SendRecommendation,
)

logger = logging.getLogger(__name__)

COPY_CACHE_TTL_SECONDS = 900
COPY_LOCK_TTL_SECONDS = 60
SUGGESTION_CACHE_TTL_SECONDS = 900
SUGGESTION_LOCK_TTL_SECONDS = 60
LOCK_WAIT_TIMEOUT_SECONDS = 15.0
LOCK_WAIT_POLL_SECONDS = 0.2


def acquire_lock(key: str, ttl_seconds: int) -> str | None:
    """Acquire a Redis distributed lock and return the lock token."""
    client = get_cache_client()
    if client is None:
        return None

    token = str(uuid.uuid4())
    try:
        acquired = client.set(key, token, ex=ttl_seconds, nx=True)
        return token if acquired else None
    except Exception as exc:
        logger.warning("[GRAPH_LOCK] Failed to acquire lock key=%s: %s", key, exc)
        return None


def release_lock(key: str, token: str | None) -> None:
    """Release a Redis distributed lock when the token still matches."""
    if not token:
        return

    client = get_cache_client()
    if client is None:
        return

    try:
        current = client.get(key)
        if current == token:
            client.delete(key)
    except Exception as exc:
        logger.warning("[GRAPH_LOCK] Failed to release lock key=%s: %s", key, exc)


def wait_for_json_cache(key: str, timeout_seconds: float = LOCK_WAIT_TIMEOUT_SECONDS) -> Any | None:
    """Poll a cache key until value appears or timeout expires."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        value = get_json(key)
        if value is not None:
            return value
        time.sleep(LOCK_WAIT_POLL_SECONDS)
    return None


def build_copy_cache_key(context: AgentContext, max_length: int) -> str:
    return f"cache:graph:copy:{context.sku}:{context.intent_level}:{max_length}"


def build_copy_lock_key(context: AgentContext, max_length: int) -> str:
    return f"lock:graph:copy:{context.sku}:{context.intent_level}:{max_length}"


def get_cached_copy_payload(context: AgentContext, max_length: int) -> dict[str, Any] | None:
    payload = get_json(build_copy_cache_key(context, max_length))
    return payload if isinstance(payload, dict) else None


def set_cached_copy_payload(
    context: AgentContext,
    max_length: int,
    message: str,
    llm_used: bool,
    copy_strategy: str,
) -> bool:
    payload = {
        "message": message,
        "llm_used": llm_used,
        "copy_strategy": copy_strategy,
    }
    return set_json(build_copy_cache_key(context, max_length), payload, COPY_CACHE_TTL_SECONDS)


def build_suggestion_cache_key(context: AgentContext) -> str:
    return (
        "cache:graph:suggestion:"
        f"{context.guide_id}:{context.user_id}:{context.sku}:"
        f"{context.intent_level}:{int(bool(context.extra.get('allowed', False)))}"
    )


def build_suggestion_lock_key(context: AgentContext) -> str:
    return (
        "lock:graph:suggestion:"
        f"{context.guide_id}:{context.user_id}:{context.sku}:"
        f"{context.intent_level}:{int(bool(context.extra.get('allowed', False)))}"
    )


def get_cached_suggestion(context: AgentContext) -> SalesSuggestion | None:
    payload = get_json(build_suggestion_cache_key(context))
    if not isinstance(payload, dict):
        return None
    return _deserialize_suggestion(payload)


def set_cached_suggestion(context: AgentContext, suggestion: SalesSuggestion) -> bool:
    payload = asdict(suggestion)
    return set_json(
        build_suggestion_cache_key(context),
        payload,
        SUGGESTION_CACHE_TTL_SECONDS,
    )


def _deserialize_suggestion(payload: dict[str, Any]) -> SalesSuggestion:
    message_pack = [
        MessageItem(
            type=item.get("type", "alternative"),
            strategy=item.get("strategy", ""),
            message=item.get("message", ""),
        )
        for item in payload.get("message_pack", []) or []
        if isinstance(item, dict)
    ]
    send_payload = payload.get("send_recommendation", {}) or {}
    send_recommendation = SendRecommendation(
        suggested=bool(send_payload.get("suggested", False)),
        best_timing=str(send_payload.get("best_timing", "")),
        note=str(send_payload.get("note", "")),
        risk_level=str(send_payload.get("risk_level", "")),
        next_step=str(send_payload.get("next_step", "")),
    )
    followup_playbook = [
        FollowupPlaybookItem(
            condition=item.get("condition", ""),
            reply=item.get("reply", ""),
        )
        for item in payload.get("followup_playbook", []) or []
        if isinstance(item, dict)
    ]
    return SalesSuggestion(
        intent_level=str(payload.get("intent_level", "")),
        confidence=str(payload.get("confidence", "")),
        why_now=str(payload.get("why_now", "")),
        recommended_action=str(payload.get("recommended_action", "")),
        action_explanation=str(payload.get("action_explanation", "")),
        message_pack=message_pack,
        send_recommendation=send_recommendation,
        followup_playbook=followup_playbook,
    )
