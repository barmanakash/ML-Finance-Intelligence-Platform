"""POST /api/v1/imports (CSV upload), GET /api/v1/imports, GET /api/v1/imports/{id}."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pymongo.database import Database

from app.config import get_settings
from app.dependencies import get_current_user, get_database
from app.exceptions import NotFoundError
from app.models.transaction_import import TransactionImportDocument
from app.models.user import UserDocument
from app.repositories.anomaly_repository import AnomalyRepository
from app.repositories.transaction_import_repository import TransactionImportRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction_import import (
    ImportListResponse,
    ImportResponse,
    ImportRowErrorResponse,
)
from app.services.anomaly_detection_service import AnomalyDetectionService
from app.services.transaction_import_service import TransactionImportService

router = APIRouter(prefix="/imports", tags=["imports"])


def get_import_service(
    db: Annotated[Database, Depends(get_database)],
) -> TransactionImportService:
    anomaly_service = AnomalyDetectionService(TransactionRepository(db), AnomalyRepository(db))
    return TransactionImportService(
        TransactionRepository(db), TransactionImportRepository(db), anomaly_service
    )


def _to_response(record: TransactionImportDocument) -> ImportResponse:
    return ImportResponse(
        id=record.id,
        filename=record.filename,
        status=record.status,
        total_rows=record.total_rows,
        imported_rows=record.imported_rows,
        failed_rows=record.failed_rows,
        errors=[ImportRowErrorResponse(row=e.row, message=e.message) for e in record.errors],
        created_at=record.created_at,
    )


@router.post(
    "",
    response_model=ImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a CSV file of transactions",
)
async def upload_csv(
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    import_service: Annotated[TransactionImportService, Depends(get_import_service)],
    file: Annotated[UploadFile, File()],
) -> ImportResponse:
    settings = get_settings()

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only .csv files are supported")

    raw_bytes = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(raw_bytes) > max_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds the {settings.max_upload_size_mb}MB upload limit",
        )
    if not raw_bytes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is empty")

    record = import_service.import_csv(current_user.id, file.filename, raw_bytes)
    return _to_response(record)


@router.get("", response_model=ImportListResponse, summary="List past imports")
def list_imports(
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> ImportListResponse:
    repo = TransactionImportRepository(db)
    items, total = repo.list_for_user(current_user.id, skip=skip, limit=limit)
    return ImportListResponse(
        items=[_to_response(i) for i in items], total=total, skip=skip, limit=limit
    )


@router.get("/{import_id}", response_model=ImportResponse, summary="Get one import's summary")
def get_import(
    import_id: str,
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
) -> ImportResponse:
    repo = TransactionImportRepository(db)
    record = repo.get_by_id(import_id, current_user.id)
    if record is None:
        raise NotFoundError("Import not found")
    return _to_response(record)
