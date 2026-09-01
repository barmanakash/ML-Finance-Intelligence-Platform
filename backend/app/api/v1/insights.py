"""POST /api/v1/insights/generate (re-run the rules engine),
GET /api/v1/insights.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.dependencies import get_current_user, get_database
from app.models.insight import InsightDocument
from app.models.user import UserDocument
from app.repositories.insight_repository import InsightRepository
from app.repositories.recurring_repository import RecurringRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.insight import InsightGenerateResponse, InsightListResponse, InsightResponse
from app.services.insights_engine import InsightsEngine

router = APIRouter(prefix="/insights", tags=["insights"])


def get_insights_engine(db: Annotated[Database, Depends(get_database)]) -> InsightsEngine:
    return InsightsEngine(
        TransactionRepository(db), RecurringRepository(db), InsightRepository(db)
    )


def _to_response(doc: InsightDocument) -> InsightResponse:
    return InsightResponse(id=doc.id, type=doc.type, message=doc.message, created_at=doc.created_at)


@router.post(
    "/generate",
    response_model=InsightGenerateResponse,
    summary="Re-generate financial insights for the current user",
)
def generate_insights(
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    engine: Annotated[InsightsEngine, Depends(get_insights_engine)],
) -> InsightGenerateResponse:
    result = engine.generate_for_user(current_user.id)
    return InsightGenerateResponse(**result)


@router.get("", response_model=InsightListResponse, summary="List generated insights")
def list_insights(
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
) -> InsightListResponse:
    repo = InsightRepository(db)
    items = repo.list_for_user(current_user.id)
    return InsightListResponse(items=[_to_response(i) for i in items])
