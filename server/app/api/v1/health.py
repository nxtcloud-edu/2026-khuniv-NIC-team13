from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.common import HealthData, SuccessResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=SuccessResponse[HealthData])
def health_check() -> SuccessResponse[HealthData]:
    settings = get_settings()
    return SuccessResponse(
        message="OK",
        data=HealthData(
            status="ok",
            app=settings.app_name,
            env=settings.app_env,
        ),
    )
