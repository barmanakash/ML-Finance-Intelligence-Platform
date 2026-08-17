"""POST /api/v1/anomalies/detect (re-scan), GET /api/v1/anomalies,
GET /api/v1/anomalies/{id}.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pymongo.database import Database

from app.dependencies import get_current_user, get_database
from app.exceptions import NotFoundError
from app.models.anomaly import AnomalyDocument
from app.models.user import UserDocument
from app.repositories.anomaly_repository import AnomalyRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.anomaly import AnomalyListResponse, AnomalyResponse, AnomalyScanResponse
from app.services.anomaly_detection_service import AnomalyDetectionService

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


def get_anomaly_service(db: Annotated[Database, Depends(get_database)]) -> AnomalyDetectionService:
    return AnomalyDetectionService(TransactionRepository(db), AnomalyRepository(db))


def _to_response(doc: AnomalyDocument) -> AnomalyResponse:
    return AnomalyResponse(
        id=doc.id,
        transaction_id=doc.transaction_id,
        anomaly_score=doc.anomaly_score,
        severity=doc.severity,
        reason=doc.reason,
        created_at=doc.created_at,
    )


@router.post(
    "/detect",
    response_model=AnomalyScanResponse,
    summary="Re-scan the user's transactions for anomalies",
)
def detect_anomalies(
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    service: Annotated[AnomalyDetectionService, Depends(get_anomaly_service)],
) -> AnomalyScanResponse:
    result = service.detect_for_user(current_user.id)
    return AnomalyScanResponse(**result)


@router.get("", response_model=AnomalyListResponse, summary="List detected anomalies")
def list_anomalies(
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    severity: str | None = Query(None, pattern="^(low|medium|high)$"),
) -> AnomalyListResponse:
    repo = AnomalyRepository(db)
    items, total = repo.list_for_user(current_user.id, skip=skip, limit=limit, severity=severity)
    return AnomalyListResponse(items=[_to_response(i) for i in items], total=total, skip=skip, limit=limit)


@router.get("/{anomaly_id}", response_model=AnomalyResponse, summary="Get one anomaly")
def get_anomaly(
    anomaly_id: str,
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
) -> AnomalyResponse:
    repo = AnomalyRepository(db)
    record = repo.get_by_id(anomaly_id, current_user.id)
    if record is None:
        raise NotFoundError("Anomaly not found")
    return _to_response(record)
