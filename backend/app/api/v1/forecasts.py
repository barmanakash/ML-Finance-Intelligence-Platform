"""POST /api/v1/forecasts/generate (recompute all periods),
GET /api/v1/forecasts (list all periods), GET /api/v1/forecasts/{period}.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.dependencies import get_current_user, get_database
from app.exceptions import NotFoundError
from app.models.forecast import ForecastDocument
from app.models.user import UserDocument
from app.repositories.forecast_repository import ForecastRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.forecast import ForecastGenerateResponse, ForecastListResponse, ForecastResponse
from app.services.forecast_service import ForecastService

router = APIRouter(prefix="/forecasts", tags=["forecasts"])

VALID_PERIODS = {"7d", "30d", "90d"}


def get_forecast_service(db: Annotated[Database, Depends(get_database)]) -> ForecastService:
    return ForecastService(TransactionRepository(db), ForecastRepository(db))


def _to_response(doc: ForecastDocument) -> ForecastResponse:
    return ForecastResponse(
        period=doc.period,
        method=doc.method,
        daily_predictions=doc.daily_predictions,
        predicted_total=doc.predicted_total,
        start_date=doc.start_date,
        end_date=doc.end_date,
        generated_at=doc.generated_at,
    )


@router.post(
    "/generate",
    response_model=ForecastGenerateResponse,
    summary="Generate/refresh expense forecasts (7d, 30d, 90d) for the current user",
)
def generate_forecasts(
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    service: Annotated[ForecastService, Depends(get_forecast_service)],
) -> ForecastGenerateResponse:
    result = service.generate_for_user(current_user.id)
    return ForecastGenerateResponse(**result)


@router.get("", response_model=ForecastListResponse, summary="List all generated forecasts")
def list_forecasts(
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
) -> ForecastListResponse:
    repo = ForecastRepository(db)
    items = repo.list_for_user(current_user.id)
    return ForecastListResponse(items=[_to_response(i) for i in items])


@router.get("/{period}", response_model=ForecastResponse, summary="Get the forecast for one period")
def get_forecast(
    period: str,
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
) -> ForecastResponse:
    if period not in VALID_PERIODS:
        raise NotFoundError(f"Unknown period '{period}'. Valid periods: {sorted(VALID_PERIODS)}")
    repo = ForecastRepository(db)
    record = repo.get_by_period(current_user.id, period)
    if record is None:
        raise NotFoundError(
            f"No forecast available for period '{period}' yet — "
            "call POST /api/v1/forecasts/generate first."
        )
    return _to_response(record)
