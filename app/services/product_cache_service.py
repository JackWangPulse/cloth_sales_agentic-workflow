"""Cache-aside helper for product lookup by SKU."""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.product import Product
from app.repositories.product_repository import get_product_by_sku
from app.services.cache_service import get_json, set_json

PRODUCT_CACHE_TTL_SECONDS = 1800

logger = logging.getLogger(__name__)


def get_product_cache_key(sku: str) -> str:
    return f"product:sku:{sku}"


def _datetime_to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


def product_to_payload(product: Product) -> dict[str, Any]:
    return {
        "id": getattr(product, "id", None),
        "brand_code": getattr(product, "brand_code", None),
        "sku": product.sku,
        "name": product.name,
        "price": float(product.price),
        "tags": product.tags,
        "attributes": product.attributes,
        "description": getattr(product, "description", None),
        "image_url": getattr(product, "image_url", None),
        "created_at": _datetime_to_iso(getattr(product, "created_at", None)),
        "updated_at": _datetime_to_iso(getattr(product, "updated_at", None)),
    }


def product_from_payload(payload: dict[str, Any]) -> Product:
    product = Product(
        brand_code=payload.get("brand_code") or "",
        sku=payload["sku"],
        name=payload["name"],
        price=Decimal(str(payload["price"])),
        tags=payload.get("tags"),
        attributes=payload.get("attributes"),
        description=payload.get("description"),
        image_url=payload.get("image_url"),
    )
    if payload.get("id") is not None:
        product.id = payload["id"]
    return product


def get_cached_product_payload(sku: str) -> dict[str, Any] | None:
    cached = get_json(get_product_cache_key(sku))
    if isinstance(cached, dict):
        return cached
    return None


def get_product_by_sku_cached(db: Session, sku: str) -> Product | None:
    product, _ = get_product_by_sku_cached_with_status(db, sku)
    return product


def get_product_by_sku_cached_with_status(
    db: Session,
    sku: str,
) -> tuple[Product | None, str]:
    cache_key = get_product_cache_key(sku)
    payload = get_cached_product_payload(sku)
    if payload:
        logger.info("[CACHE] HIT domain=product key=%s", cache_key)
        return product_from_payload(payload), "hit"

    logger.info("[CACHE] MISS domain=product key=%s", cache_key)
    product = get_product_by_sku(db, sku)
    if product is None:
        return None, "miss"

    set_json(
        cache_key,
        product_to_payload(product),
        PRODUCT_CACHE_TTL_SECONDS,
    )
    return product, "miss"
