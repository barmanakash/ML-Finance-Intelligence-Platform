"""Orchestrates CSV upload -> parse -> validate -> persist.

Whole-file duplicate imports are rejected proactively by checking
(user_id, file_hash) against `transaction_imports` before doing any work;
the collection also has a unique index on that pair (see
scripts/create_indexes.py) as a second line of defense against races.
"""

import hashlib

from app.exceptions import ConflictError, ValidationAppError
from app.models.transaction import TransactionDocument
from app.models.transaction_import import ImportRowError, TransactionImportDocument
from app.repositories.transaction_import_repository import TransactionImportRepository
from app.repositories.transaction_repository import TransactionRepository
from app.utils.csv_parser import ParsedRow, compute_file_hash, parse_csv

MAX_STORED_ERRORS = 50


class TransactionImportService:
    def __init__(
        self,
        transaction_repo: TransactionRepository,
        import_repo: TransactionImportRepository,
    ) -> None:
        self._transaction_repo = transaction_repo
        self._import_repo = import_repo

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
            transactions = [
                TransactionDocument(
                    user_id=user_id,
                    transaction_date=row.transaction_date,
                    description=row.description,
                    merchant=row.merchant,
                    amount=row.amount,
                    currency=row.currency,
                    transaction_type=row.transaction_type,
                    import_id=saved_import.id,
                    reference=row.reference,
                    content_hash=self._content_hash(user_id, row),
                )
                for row in parse_result.rows
            ]
            self._transaction_repo.bulk_create(transactions)

        return saved_import

    @staticmethod
    def _content_hash(user_id: str, row: ParsedRow) -> str:
        raw = (
            f"{user_id}|{row.transaction_date.isoformat()}|"
            f"{row.description}|{row.amount}|{row.transaction_type}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()
