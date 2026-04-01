"""Cache-aside helpers for behavior summary and intent classification."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.behavior_repository import get_recent_behavior
from app.services.cache_service import get_json, set_json
from app.services.intent_engine import classify_intent

BEHAVIOR_CACHE_TTL_SECONDS = 300
NO_BEHAVIOR_REASON = "无行为记录，无法分析购买意图"

logger = logging.getLogger(__name__)


def get_behavior_summary_cache_key(
    *, guide_id: str, user_id: str, sku: str, limit: int
) -> str:
    return f"behavior_summary:{guide_id}:{user_id}:{sku}:{limit}"


def get_intent_cache_key(*, guide_id: str, user_id: str, sku: str, limit: int) -> str:
    return f"intent:{guide_id}:{user_id}:{sku}:{limit}"


def empty_behavior_summary() -> dict[str, Any]:
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


def summarize_behavior_logs(logs: list[Any]) -> dict[str, Any]:
    if not logs:
        return empty_behavior_summary()

    stay_seconds_list = [log.stay_seconds for log in logs]
    total_stay_seconds = sum(stay_seconds_list)
    event_types = [log.event_type for log in logs]
    event_type_counts: dict[str, int] = {}
    for event_type in event_types:
        event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1

    return {
        "visit_count": len(logs),
        "max_stay_seconds": max(stay_seconds_list) if stay_seconds_list else 0,
        "avg_stay_seconds": round(total_stay_seconds / len(logs), 2),
        "total_stay_seconds": total_stay_seconds,
        "has_enter_buy_page": "enter_buy_page" in event_types,
        "has_favorite": "favorite" in event_types,
        "has_share": "share" in event_types,
        "has_click_size_chart": "click_size_chart" in event_types,
        "event_types": list(set(event_types)),
        "event_type_counts": event_type_counts,
    }


async def get_behavior_summary_cached(
    *,
    db: Session,
    guide_id: str,
    user_id: str,
    sku: str,
    limit: int,
) -> dict[str, Any]:
    summary, _ = await get_behavior_summary_cached_with_status(
        db=db,
        guide_id=guide_id,
        user_id=user_id,
        sku=sku,
        limit=limit,
    )
    return summary


async def get_behavior_summary_cached_with_status(
    *,
    db: Session,
    guide_id: str,
    user_id: str,
    sku: str,
    limit: int,
) -> tuple[dict[str, Any], str]:
    cache_key = get_behavior_summary_cache_key(
        guide_id=guide_id,
        user_id=user_id,
        sku=sku,
        limit=limit,
    )
    cached = get_json(cache_key)
    if isinstance(cached, dict):
        logger.info("[CACHE] HIT domain=behavior_summary key=%s", cache_key)
        return cached, "hit"

    logger.info("[CACHE] MISS domain=behavior_summary key=%s", cache_key)
    logs = await get_recent_behavior(
        db=db,
        guide_id=guide_id,
        user_id=user_id,
        sku=sku,
        limit=limit,
    )
    summary = summarize_behavior_logs(logs)
    set_json(cache_key, summary, BEHAVIOR_CACHE_TTL_SECONDS)
    return summary, "miss"


async def get_intent_result_cached(
    *,
    db: Session,
    guide_id: str,
    user_id: str,
    sku: str,
    limit: int,
) -> dict[str, Any]:
    result, _ = await get_intent_result_cached_with_status(
        db=db,
        guide_id=guide_id,
        user_id=user_id,
        sku=sku,
        limit=limit,
    )
    return result


async def get_intent_result_cached_with_status(
    *,
    db: Session,
    guide_id: str,
    user_id: str,
    sku: str,
    limit: int,
) -> tuple[dict[str, Any], str]:
    cache_key = get_intent_cache_key(
        guide_id=guide_id,
        user_id=user_id,
        sku=sku,
        limit=limit,
    )
    cached = get_json(cache_key)
    if isinstance(cached, dict):
        logger.info("[CACHE] HIT domain=intent key=%s", cache_key)
        return cached, "hit"

    logger.info("[CACHE] MISS domain=intent key=%s", cache_key)
    summary, _ = await get_behavior_summary_cached_with_status(
        db=db,
        guide_id=guide_id,
        user_id=user_id,
        sku=sku,
        limit=limit,
    )
    if summary["visit_count"] == 0:
        result = {
            "intent_level": "low",
            "reason": NO_BEHAVIOR_REASON,
            "behavior_summary": summary,
        }
    else:
        intent_result = classify_intent(summary)
        result = {
            "intent_level": intent_result.level,
            "reason": intent_result.reason,
            "behavior_summary": summary,
        }

    set_json(cache_key, result, BEHAVIOR_CACHE_TTL_SECONDS)
    return result, "miss"
