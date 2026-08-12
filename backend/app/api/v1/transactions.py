"""GET /api/v1/transactions, GET /api/v1/transactions/{id}."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pymongo.database import Database

from app.dependencies import get_current_user, get_database
from app.exceptions import NotFoundError
from app.models.transaction import TransactionDocument
from app.models.user import UserDocument
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction import TransactionListResponse, TransactionResponse

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _to_response(doc: TransactionDocument) -> TransactionResponse:
    return TransactionResponse(
        id=doc.id,
        transaction_date=doc.transaction_date,
        description=doc.description,
        merchant=doc.merchant,
        amount=doc.amount,
        currency=doc.currency,
        transaction_type=doc.transaction_type,
        category=doc.category,
        is_anomaly=doc.is_anomaly,
        anomaly_score=doc.anomaly_score,
        import_id=doc.import_id,
        reference=doc.reference,
        created_at=doc.created_at,
    )


@router.get("", response_model=TransactionListResponse, summary="List the user's transactions")
def list_transactions(
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    category: str | None = Query(None),
    transaction_type: str | None = Query(None, pattern="^(debit|credit)$"),
    import_id: str | None = Query(None),
) -> TransactionListResponse:
    repo = TransactionRepository(db)
    items, total = repo.list_for_user(
        current_user.id,
        skip=skip,
        limit=limit,
        category=category,
        transaction_type=transaction_type,
        import_id=import_id,
    )
    return TransactionListResponse(
        items=[_to_response(t) for t in items], total=total, skip=skip, limit=limit
    )


@router.get("/{transaction_id}", response_model=TransactionResponse, summary="Get one transaction")
def get_transaction(
    transaction_id: str,
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
) -> TransactionResponse:
    repo = TransactionRepository(db)
    doc = repo.get_by_id(transaction_id, current_user.id)
    if doc is None:
        raise NotFoundError("Transaction not found")
    return _to_response(doc)
