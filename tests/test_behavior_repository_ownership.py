"""Tests for strict guide ownership filtering in behavior queries."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.repositories.behavior_repository import get_recent_behavior


@pytest.mark.asyncio
async def test_get_recent_behavior_filters_by_guide_id():
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = []

    db = MagicMock()
    db.query.return_value = mock_query

    await get_recent_behavior(
        db=db,
        user_id="user_001",
        guide_id="guide_001",
        sku="8WZ01CM1",
        limit=10,
    )

    filter_args = mock_query.filter.call_args[0]
    assert len(filter_args) == 3


def test_get_recent_behavior_requires_guide_id_parameter():
    with pytest.raises(TypeError):
        get_recent_behavior(  # type: ignore[misc]
            db=MagicMock(),
            user_id="user_001",
            sku="8WZ01CM1",
            limit=10,
        )
