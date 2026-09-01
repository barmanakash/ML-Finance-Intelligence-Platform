"""GET /api/v1/ml/models (registry status), POST /api/v1/ml/categorize
(on-demand categorization, useful for previewing/re-categorizing a single
transaction description without a full CSV re-import).
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies import get_current_user
from app.models.user import UserDocument
from app.services.anomaly_detection_service import get_anomaly_detector_status
from app.services.categorization_service import categorization_service
from app.services.forecast_service import get_forecaster_status

router = APIRouter(prefix="/ml", tags=["ml"])


class CategorizeRequest(BaseModel):
    description: str = Field(min_length=1, max_length=500)


class CategorizeResponse(BaseModel):
    category: str
    confidence: float


class ModelStatusResponse(BaseModel):
    model_name: str
    is_ready: bool
    active_version: int | None


@router.get("/models", response_model=list[ModelStatusResponse], summary="Model registry status")
def get_model_status(
    current_user: Annotated[UserDocument, Depends(get_current_user)],
) -> list[ModelStatusResponse]:
    anomaly_ready, anomaly_version = get_anomaly_detector_status()
    forecaster_ready, forecaster_version = get_forecaster_status()
    return [
        ModelStatusResponse(
            model_name="transaction-classifier",
            is_ready=categorization_service.is_ready,
            active_version=categorization_service.active_version,
        ),
        ModelStatusResponse(
            model_name="anomaly-detector",
            is_ready=anomaly_ready,
            active_version=anomaly_version,
        ),
        ModelStatusResponse(
            model_name="expense-forecaster",
            is_ready=forecaster_ready,
            active_version=forecaster_version,
        ),
    ]


@router.post(
    "/categorize",
    response_model=CategorizeResponse,
    summary="Categorize a transaction description on demand",
)
def categorize(
    payload: CategorizeRequest,
    current_user: Annotated[UserDocument, Depends(get_current_user)],
) -> CategorizeResponse:
    prediction = categorization_service.categorize(payload.description)
    return CategorizeResponse(category=prediction.category, confidence=prediction.confidence)
