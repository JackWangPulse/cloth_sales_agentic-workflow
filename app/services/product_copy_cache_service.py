"""Redis cache helpers for product copy candidates."""
from __future__ import annotations

from typing import Any

from app.services.cache_service import get_json, set_json

PRODUCT_COPY_CACHE_TTL_SECONDS = 1800


def build_product_copy_cache_key(
    sku: str,
    scene: str,
    style: str,
    max_length: int,
) -> str:
    return f"cache:product_copy:{sku}:{scene}:{style}:{max_length}"


def get_cached_product_copy_candidates(
    sku: str,
    scene: str,
    style: str,
    max_length: int,
) -> list[dict[str, Any]] | None:
    payload = get_json(build_product_copy_cache_key(sku, scene, style, max_length))
    if not isinstance(payload, list):
        return None
    return [item for item in payload if isinstance(item, dict)]


def set_cached_product_copy_candidates(
    sku: str,
    scene: str,
    style: str,
    max_length: int,
    copy_candidates: list[dict[str, Any]],
) -> bool:
    return set_json(
        build_product_copy_cache_key(sku, scene, style, max_length),
        copy_candidates,
        PRODUCT_COPY_CACHE_TTL_SECONDS,
    )
