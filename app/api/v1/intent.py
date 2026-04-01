"""Intent analysis API endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.intent_schemas import (
    BehaviorSummary,
    IntentAnalysisRequest,
    IntentAnalysisResponse,
)
from app.services.behavior_cache_service import (
    NO_BEHAVIOR_REASON,
    get_intent_result_cached,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai", "intent"])


@router.post("/analyze/intent", response_model=IntentAnalysisResponse)
async def analyze_intent(
    request: IntentAnalysisRequest,
    db: Session = Depends(get_db),
) -> IntentAnalysisResponse:
    logger.info("=" * 80)
    logger.info("[API] POST /ai/analyze/intent - Request received")
    logger.info(
        "[API] Request parameters: user_id=%s, guide_id=%s, sku=%s, limit=%s",
        request.user_id,
        request.guide_id,
        request.sku,
        request.limit,
    )

    try:
        intent_result = await get_intent_result_cached(
            db=db,
            guide_id=request.guide_id,
            user_id=request.user_id,
            sku=request.sku,
            limit=request.limit,
        )
        summary_dict = intent_result["behavior_summary"]
        total_logs_analyzed = int(summary_dict.get("visit_count", 0))

        if total_logs_analyzed == 0:
            logger.warning(
                "[API] No behavior logs found for user_id=%s, guide_id=%s, sku=%s",
                request.user_id,
                request.guide_id,
                request.sku,
            )
            return IntentAnalysisResponse(
                user_id=request.user_id,
                sku=request.sku,
                intent_level="low",
                reason=NO_BEHAVIOR_REASON,
                behavior_summary=None,
                total_logs_analyzed=0,
            )

        behavior_summary = BehaviorSummary(
            visit_count=summary_dict["visit_count"],
            max_stay_seconds=summary_dict["max_stay_seconds"],
            avg_stay_seconds=summary_dict["avg_stay_seconds"],
            total_stay_seconds=summary_dict["total_stay_seconds"],
            has_enter_buy_page=summary_dict["has_enter_buy_page"],
            has_favorite=summary_dict["has_favorite"],
            has_share=summary_dict["has_share"],
            has_click_size_chart=summary_dict["has_click_size_chart"],
            event_types=summary_dict["event_types"],
            event_type_counts=summary_dict.get("event_type_counts", {}),
        )

        response = IntentAnalysisResponse(
            user_id=request.user_id,
            sku=request.sku,
            intent_level=intent_result["intent_level"],
            reason=intent_result["reason"],
            behavior_summary=behavior_summary,
            total_logs_analyzed=total_logs_analyzed,
        )

        logger.info(
            "[API] Intent resolved from cache-backed path: intent=%s visits=%s",
            intent_result["intent_level"],
            total_logs_analyzed,
        )
        logger.info("=" * 80)
        return response
    except HTTPException:
        logger.info("=" * 80)
        raise
    except Exception as exc:
        logger.error(
            "[API] Unexpected error in analyze_intent endpoint: %s",
            exc,
            exc_info=True,
        )
        logger.info("=" * 80)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze intent: {str(exc)}",
        )
