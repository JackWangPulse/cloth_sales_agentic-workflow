"""Follow-up suggestion API endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.followup_schemas import (
    FollowupRequest,
    FollowupResponse,
    FollowupResponseData,
)
from app.services.behavior_cache_service import get_intent_result_cached
from app.services.followup_service import generate_followup_suggestion
from app.services.product_cache_service import get_product_by_sku_cached

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai", "followup"])


@router.post("/followup/suggest", response_model=FollowupResponse)
async def suggest_followup(
    request: FollowupRequest,
    db: Session = Depends(get_db),
) -> FollowupResponse:
    logger.info("=" * 80)
    logger.info("[API] POST /ai/followup/suggest - Request received")
    logger.info(
        "[API] Request parameters: user_id=%s, guide_id=%s, sku=%s, limit=%s",
        request.user_id,
        request.guide_id,
        request.sku,
        request.limit,
    )

    try:
        product = get_product_by_sku_cached(db, request.sku)
        if not product:
            logger.warning("[API] Product not found: sku=%s", request.sku)
            raise HTTPException(
                status_code=404,
                detail=f"Product with SKU {request.sku} not found",
            )

        intent_result = await get_intent_result_cached(
            db=db,
            guide_id=request.guide_id,
            user_id=request.user_id,
            sku=request.sku,
            limit=request.limit,
        )
        summary = intent_result["behavior_summary"]
        total_logs_analyzed = int(summary.get("visit_count", 0))
        intention_level = (
            "low" if total_logs_analyzed == 0 else intent_result["intent_level"]
        )

        followup_result = await generate_followup_suggestion(
            product=product,
            summary=summary,
            intention_level=intention_level,
        )

        response_data = FollowupResponseData(
            user_id=request.user_id,
            sku=request.sku,
            product_name=product.name,
            intention_level=intention_level,
            suggested_action=followup_result["suggested_action"],
            message=followup_result["message"],
            behavior_summary=summary if total_logs_analyzed else None,
            total_logs_analyzed=total_logs_analyzed,
        )

        logger.info(
            "[API] Follow-up suggestion generated: intent=%s action=%s",
            intention_level,
            followup_result["suggested_action"],
        )
        logger.info("=" * 80)
        return FollowupResponse(
            success=True,
            message="Follow-up suggestion generated successfully",
            data=response_data,
        )
    except HTTPException:
        logger.info("=" * 80)
        raise
    except Exception as exc:
        logger.error(
            "[API] Unexpected error in suggest_followup endpoint: %s",
            exc,
            exc_info=True,
        )
        logger.info("=" * 80)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate follow-up suggestion: {str(exc)}",
        )
