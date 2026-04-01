"""Tests for product cache service."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.models.product import Product
from app.services.product_cache_service import (
    PRODUCT_CACHE_TTL_SECONDS,
    get_product_by_sku_cached,
    get_product_cache_key,
)


def test_product_cache_key_generation():
    assert get_product_cache_key("8WZ01CM1") == "product:sku:8WZ01CM1"


def test_product_cache_hit_returns_cached_product_payload():
    payload = {
        "brand_code": "BELLE",
        "sku": "8WZ01CM1",
        "name": "运动鞋",
        "price": 458.0,
        "tags": ["百搭"],
        "attributes": {"scene": "运动"},
        "description": None,
        "image_url": None,
    }

    with patch(
        "app.services.product_cache_service.get_cached_product_payload",
        return_value=payload,
    ), patch(
        "app.services.product_cache_service.get_product_by_sku"
    ) as mocked_repo:
        product = get_product_by_sku_cached(MagicMock(), "8WZ01CM1")

    mocked_repo.assert_not_called()
    assert product is not None
    assert product.sku == "8WZ01CM1"
    assert product.brand_code == "BELLE"


def test_product_cache_miss_loads_from_db_and_backfills():
    db = MagicMock()
    product = Product(
        brand_code="BELLE",
        sku="8WZ01CM1",
        name="运动鞋",
        price=Decimal("458.00"),
        tags=["百搭"],
        attributes={"scene": "运动"},
    )

    with patch(
        "app.services.product_cache_service.get_cached_product_payload",
        return_value=None,
    ), patch(
        "app.services.product_cache_service.get_product_by_sku",
        return_value=product,
    ) as mocked_repo, patch(
        "app.services.product_cache_service.set_json",
        return_value=True,
    ) as mocked_set:
        result = get_product_by_sku_cached(db, "8WZ01CM1")

    assert result is product
    mocked_repo.assert_called_once_with(db, "8WZ01CM1")
    mocked_set.assert_called_once()
    args = mocked_set.call_args[0]
    assert args[0] == "product:sku:8WZ01CM1"
    assert args[2] == PRODUCT_CACHE_TTL_SECONDS
