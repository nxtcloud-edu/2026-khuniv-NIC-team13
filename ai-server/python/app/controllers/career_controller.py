"""Career job recommendation HTTP endpoint."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.career.errors import CareerConfigurationError
from app.schemas.career import (
    CareerRoadmapRequest,
    CareerRoadmapResponse,
    CompanyRecommendationRequest,
    CompanyRecommendationResponse,
    JobRecommendationRequest,
    JobRecommendationResponse,
)

router = APIRouter(prefix="/api/career", tags=["career"])


@router.post("/recommendations", response_model=JobRecommendationResponse)
async def recommend_jobs(
    payload: JobRecommendationRequest, request: Request
) -> JobRecommendationResponse:
    try:
        return await request.app.state.container.career_service.recommend(payload)
    except CareerConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post(
    "/company-recommendations", response_model=CompanyRecommendationResponse
)
async def recommend_companies(
    payload: CompanyRecommendationRequest, request: Request
) -> CompanyRecommendationResponse:
    try:
        return await request.app.state.container.career_service.recommend_companies(
            payload
        )
    except CareerConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/roadmap", response_model=CareerRoadmapResponse)
async def create_career_roadmap(
    payload: CareerRoadmapRequest, request: Request
) -> CareerRoadmapResponse:
    try:
        return await request.app.state.container.career_service.roadmap(payload)
    except CareerConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
