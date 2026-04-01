"""Tests for safe Redis cache helper."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services import cache_service


def test_get_cache_client_returns_none_without_redis_url():
    cache_service._redis_client = None
    settings = MagicMock(redis_url=None)

    with patch("app.services.cache_service.get_settings", return_value=settings):
        assert cache_service.get_cache_client() is None


def test_get_json_returns_parsed_payload():
    client = MagicMock()
    client.get.return_value = '{"sku":"8WZ01CM1"}'

    with patch("app.services.cache_service.get_cache_client", return_value=client):
        payload = cache_service.get_json("product:sku:8WZ01CM1")

    assert payload == {"sku": "8WZ01CM1"}


def test_get_json_degrades_to_cache_miss_on_exception():
    client = MagicMock()
    client.get.side_effect = RuntimeError("redis down")

    with patch("app.services.cache_service.get_cache_client", return_value=client):
        assert cache_service.get_json("broken") is None
