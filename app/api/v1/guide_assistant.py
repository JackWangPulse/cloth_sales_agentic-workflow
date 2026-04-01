"""Unified guide assistant API endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from app.schemas.base_schemas import BaseResponse
from app.schemas.guide_assistant_schemas import (
    GuideAssistantRequest,
    GuideAssistantResponse,
)
from app.services.guide_assistant_router import route_guide_request
from app.services.guide_assistant_service import execute_guide_request

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post(
    "/guide/assistant",
    response_model=BaseResponse[GuideAssistantResponse],
)
async def guide_assistant(
    request: GuideAssistantRequest,
) -> BaseResponse[GuideAssistantResponse]:
    """Route a guide request to the appropriate internal capability."""
    decision = route_guide_request(request)
    payload = await execute_guide_request(decision)
    return BaseResponse(
        success=True,
        message="Guide assistant request executed successfully",
        data=payload,
    )
