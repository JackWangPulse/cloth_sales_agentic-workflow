"""Product tool for fetching product information."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.agents.context import AgentContext
from app.services.product_cache_service import get_product_by_sku_cached_with_status

logger = logging.getLogger(__name__)


async def fetch_product(
    context: AgentContext,
    db: Session,
    **kwargs: Any,
) -> AgentContext:
    """Load product info into the shared agent context."""
    logger.info("=" * 80)
    logger.info("[PRODUCT_TOOL] Fetching product information")
    logger.info("[PRODUCT_TOOL] Context SKU: %s", context.sku)

    if not context.sku:
        error_msg = "SKU is required in context to fetch product"
        logger.error("[PRODUCT_TOOL] %s", error_msg)
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        product, cache_status = get_product_by_sku_cached_with_status(db, context.sku)
        if not product:
            error_msg = f"Product with SKU {context.sku} not found"
            logger.error("[PRODUCT_TOOL] %s", error_msg)
            raise HTTPException(status_code=404, detail=error_msg)

        context.product = product
        context.extra.setdefault("cache_diagnostics", {})["product"] = cache_status

        logger.info(
            "[PRODUCT_TOOL] Product loaded: id=%s, name=%s, price=%s, cache=%s",
            product.id,
            product.name,
            product.price,
            cache_status,
        )
        logger.info("=" * 80)
        return context
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[PRODUCT_TOOL] Error fetching product: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch product: {str(exc)}",
        )
