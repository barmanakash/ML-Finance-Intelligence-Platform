"""POST /api/v1/recurring/detect (re-scan), GET /api/v1/recurring,
GET /api/v1/recurring/{id}.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pymongo.database import Database

from app.dependencies import get_current_user, get_database
from app.exceptions import NotFoundError
from app.models.recurring import RecurringDocument
from app.models.user import UserDocument
from app.repositories.recurring_repository import RecurringRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.recurring import RecurringListResponse, RecurringResponse, RecurringScanResponse
from app.services.recurring_detection_service import RecurringDetectionService

router = APIRouter(prefix="/recurring", tags=["recurring"])


def get_recurring_service(
    db: Annotated[Database, Depends(get_database)],
) -> RecurringDetectionService:
    return RecurringDetectionService(TransactionRepository(db), RecurringRepository(db))


def _to_response(doc: RecurringDocument) -> RecurringResponse:
    return RecurringResponse(
        id=doc.id,
        merchant=doc.merchant,
        category=doc.category,
        frequency=doc.frequency,
        average_amount=doc.average_amount,
        occurrences=doc.occurrences,
        confidence=doc.confidence,
        last_transaction_date=doc.last_transaction_date,
        next_expected_date=doc.next_expected_date,
    )


@router.post(
    "/detect",
    response_model=RecurringScanResponse,
    summary="Re-scan the user's transactions for recurring payments",
)
def detect_recurring(
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    service: Annotated[RecurringDetectionService, Depends(get_recurring_service)],
) -> RecurringScanResponse:
    result = service.detect_for_user(current_user.id)
    return RecurringScanResponse(**result)


@router.get("", response_model=RecurringListResponse, summary="List detected recurring payments")
def list_recurring(
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> RecurringListResponse:
    repo = RecurringRepository(db)
    items, total = repo.list_for_user(current_user.id, skip=skip, limit=limit)
    return RecurringListResponse(
        items=[_to_response(i) for i in items], total=total, skip=skip, limit=limit
    )


@router.get(
    "/{recurring_id}", response_model=RecurringResponse, summary="Get one recurring payment"
)
def get_recurring(
    recurring_id: str,
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
) -> RecurringResponse:
    repo = RecurringRepository(db)
    record = repo.get_by_id(recurring_id, current_user.id)
    if record is None:
        raise NotFoundError("Recurring payment not found")
    return _to_response(record)
