"""Runs anomaly detection over a user's full transaction history.

Re-run after every CSV import (a new transaction can shift what "normal"
looks like for a merchant/category — see ml.anomaly_detection.features),
and available on demand via POST /api/v1/anomalies/detect. Scoring always
recomputes over the complete current history rather than only the newest
batch, so z-score baselines stay correct as more data arrives; the
`anomalies` collection is kept in sync via upsert-or-delete per transaction
(see AnomalyRepository), so re-running detection is idempotent rather than
accumulating duplicates.

Path/import note: same pattern as CategorizationService — direct import
works in Docker (docker-compose mounts ./ml -> /app/ml), with a sys.path
fallback for local dev where `ml/` is a sibling of `backend/`.
"""

import logging
import sys
from pathlib import Path

import pandas as pd

from app.models.anomaly import AnomalyDocument
from app.repositories.anomaly_repository import AnomalyRepository
from app.repositories.transaction_repository import TransactionRepository

logger = logging.getLogger(__name__)

try:
    from ml.anomaly_detection.predict import AnomalyDetector
except ImportError:
    _repo_root = Path(__file__).resolve().parents[3]
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))
    from ml.anomaly_detection.predict import AnomalyDetector  # noqa: E402


class AnomalyDetectionService:
    def __init__(
        self, transaction_repo: TransactionRepository, anomaly_repo: AnomalyRepository
    ) -> None:
        self._transaction_repo = transaction_repo
        self._anomaly_repo = anomaly_repo
        try:
            self._detector: AnomalyDetector | None = AnomalyDetector()
        except Exception:
            logger.exception("Failed to load anomaly detection model")
            self._detector = None

    @property
    def is_ready(self) -> bool:
        return self._detector is not None and self._detector.is_ready

    @property
    def active_version(self) -> int | None:
        return self._detector.active_version if self._detector else None

    def detect_for_user(self, user_id: str) -> dict:
        if not self.is_ready:
            return {"scored": 0, "anomalies_found": 0, "model_ready": False}

        transactions = self._transaction_repo.list_all_for_user(user_id)
        if not transactions:
            return {"scored": 0, "anomalies_found": 0, "model_ready": True}

        assert self._detector is not None
        df = pd.DataFrame(
            [
                {
                    "amount": t.amount,
                    "category": t.category,
                    "merchant": t.merchant,
                    "transaction_date": t.transaction_date,
                }
                for t in transactions
            ]
        )
        results = self._detector.score_transactions(df)

        anomalies_found = 0
        for txn, result in zip(transactions, results):
            self._transaction_repo.update_anomaly_fields(txn.id, result.is_anomaly, result.anomaly_score)
            if result.is_anomaly:
                anomalies_found += 1
                self._anomaly_repo.upsert(
                    AnomalyDocument(
                        user_id=user_id,
                        transaction_id=txn.id,
                        anomaly_score=result.anomaly_score,
                        severity=result.severity,
                        reasons=result.reasons,
                        amount=txn.amount,
                        merchant=txn.merchant,
                        category=txn.category,
                        transaction_date=txn.transaction_date,
                    )
                )
            else:
                self._anomaly_repo.delete_for_transaction(txn.id)

        return {"scored": len(transactions), "anomalies_found": anomalies_found, "model_ready": True}
