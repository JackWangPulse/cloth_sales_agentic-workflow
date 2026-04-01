"""Tests for behavior and intent cache service."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.behavior_cache_service import (
    BEHAVIOR_CACHE_TTL_SECONDS,
    get_behavior_summary_cache_key,
    get_behavior_summary_cached,
    get_intent_cache_key,
    get_intent_result_cached,
)


def test_behavior_summary_key_generation():
    assert (
        get_behavior_summary_cache_key(
            guide_id="guide_001",
            user_id="user_001",
            sku="8WZ01CM1",
            limit=50,
        )
        == "behavior_summary:guide_001:user_001:8WZ01CM1:50"
    )


def test_intent_key_generation():
    assert (
        get_intent_cache_key(
            guide_id="guide_001",
            user_id="user_001",
            sku="8WZ01CM1",
            limit=50,
        )
        == "intent:guide_001:user_001:8WZ01CM1:50"
    )


@pytest.mark.asyncio
async def test_behavior_summary_cache_hit_bypasses_recomputation():
    cached_summary = {"visit_count": 2, "total_stay_seconds": 30}

    with patch(
        "app.services.behavior_cache_service.get_json",
        return_value=cached_summary,
    ), patch(
        "app.services.behavior_cache_service.get_recent_behavior",
        new=AsyncMock(),
    ) as mocked_repo:
        summary = await get_behavior_summary_cached(
            db=MagicMock(),
            guide_id="guide_001",
            user_id="user_001",
            sku="8WZ01CM1",
            limit=50,
        )

    mocked_repo.assert_not_awaited()
    assert summary == cached_summary


@pytest.mark.asyncio
async def test_intent_cache_miss_computes_and_backfills():
    logs = [
        SimpleNamespace(stay_seconds=45, event_type="browse"),
        SimpleNamespace(stay_seconds=30, event_type="favorite"),
    ]

    with patch(
        "app.services.behavior_cache_service.get_json",
        return_value=None,
    ), patch(
        "app.services.behavior_cache_service.get_recent_behavior",
        new=AsyncMock(return_value=logs),
    ), patch(
        "app.services.behavior_cache_service.set_json",
        return_value=True,
    ) as mocked_set:
        result = await get_intent_result_cached(
            db=MagicMock(),
            guide_id="guide_001",
            user_id="user_001",
            sku="8WZ01CM1",
            limit=50,
        )

    assert result["behavior_summary"]["visit_count"] == 2
    assert "intent_level" in result
    assert mocked_set.call_count >= 2
    assert mocked_set.call_args_list[-1][0][2] == BEHAVIOR_CACHE_TTL_SECONDS
