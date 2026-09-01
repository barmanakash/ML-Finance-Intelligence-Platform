"""Orchestrates CSV upload -> parse -> validate -> persist.

Whole-file duplicate imports are rejected proactively by checking
(user_id, file_hash) against `transaction_imports` before doing any work;
the collection also has a unique index on that pair (see
scripts/create_indexes.py) as a second line of defense against races.
"""

import hashlib
import logging

from app.exceptions import ConflictError, ValidationAppError
from app.models.transaction import TransactionDocument
from app.models.transaction_import import ImportRowError, TransactionImportDocument
from app.repositories.transaction_import_repository import TransactionImportRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.anomaly_detection_service import AnomalyDetectionService
from app.services.categorization_service import categorization_service
from app.services.forecast_service import ForecastService
from app.services.recurring_detection_service import RecurringDetectionService
from app.utils.csv_parser import ParsedRow, compute_file_hash, parse_csv

logger = logging.getLogger(__name__)

MAX_STORED_ERRORS = 50


class TransactionImportService:
    def __init__(
        self,
        transaction_repo: TransactionRepository,
        import_repo: TransactionImportRepository,
        anomaly_service: AnomalyDetectionService | None = None,
        recurring_service: RecurringDetectionService | None = None,
        forecast_service: ForecastService | None = None,
    ) -> None:
        self._transaction_repo = transaction_repo
        self._import_repo = import_repo
        self._anomaly_service = anomaly_service
        self._recurring_service = recurring_service
        self._forecast_service = forecast_service

    def import_csv(
        self, user_id: str, filename: str, raw_bytes: bytes
    ) -> TransactionImportDocument:
        file_hash = compute_file_hash(raw_bytes)

        existing = self._import_repo.get_by_hash(user_id, file_hash)
        if existing is not None:
            raise ConflictError(
                f"This file was already imported on {existing.created_at.isoformat()} "
                f"(import id: {existing.id})"
            )

        try:
            parse_result = parse_csv(raw_bytes)
        except ValueError as exc:
            raise ValidationAppError(str(exc)) from exc

        if not parse_result.rows and not parse_result.errors:
            raise ValidationAppError("The uploaded file contains no data rows.")

        if parse_result.rows:
            status = "partial" if parse_result.errors else "completed"
        else:
            status = "failed"

        import_record = TransactionImportDocument(
            user_id=user_id,
            filename=filename,
            file_hash=file_hash,
            status=status,
            total_rows=parse_result.total_rows,
            imported_rows=len(parse_result.rows),
            failed_rows=len(parse_result.errors),
            errors=[
                ImportRowError(row=e.row, message=e.message)
                for e in parse_result.errors[:MAX_STORED_ERRORS]
            ],
        )
        saved_import = self._import_repo.create(import_record)

        if parse_result.rows:
            descriptions = [row.description for row in parse_result.rows]
            predictions = categorization_service.categorize_batch(descriptions)
            transactions = [
                TransactionDocument(
                    user_id=user_id,
                    transaction_date=row.transaction_date,
                    description=row.description,
                    merchant=row.merchant,
                    amount=row.amount,
                    currency=row.currency,
                    transaction_type=row.transaction_type,
                    category=prediction.category,
                    category_confidence=prediction.confidence,
                    import_id=saved_import.id,
                    reference=row.reference,
                    content_hash=self._content_hash(user_id, row),
                )
                for row, prediction in zip(parse_result.rows, predictions)
            ]
            self._transaction_repo.bulk_create(transactions)

            # Best-effort: a new import can shift what "normal" looks like
            # for this user, so re-score their full history. A detection
            # failure must never fail the import itself.
            if self._anomaly_service is not None:
                try:
                    self._anomaly_service.detect_for_user(user_id)
                except Exception:
                    logger.exception("Anomaly detection failed after import for user_id=%s", user_id)

            # Same best-effort rationale as anomaly detection above: a new
            # import can add the 3rd+ occurrence that turns a merchant into
            # a detectable recurring pattern, so re-scan after every import.
            if self._recurring_service is not None:
                try:
                    self._recurring_service.detect_for_user(user_id)
                except Exception:
                    logger.exception("Recurring detection failed after import for user_id=%s", user_id)

            # Same best-effort rationale: new transactions shift the daily
            # spend history every forecast is built from, so refresh all
            # three forecast periods after every import.
            if self._forecast_service is not None:
                try:
                    self._forecast_service.generate_for_user(user_id)
                except Exception:
                    logger.exception("Forecast generation failed after import for user_id=%s", user_id)

        return saved_import

    @staticmethod
    def _content_hash(user_id: str, row: ParsedRow) -> str:
        raw = (
            f"{user_id}|{row.transaction_date.isoformat()}|"
            f"{row.description}|{row.amount}|{row.transaction_type}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()
