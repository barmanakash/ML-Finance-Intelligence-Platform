"""Wraps ml.anomaly_detection.predict.AnomalyDetector for use inside the
backend. Anomaly detection is fit fresh per user against their real
transaction history — see ml/anomaly_detection/predict.py for why there's
no persisted global model here (unlike categorization).

Path note: same import-path handling as categorization_service.py — works
directly in Docker (docker-compose mounts ./ml -> /app/ml), falls back to
adding the repo root to sys.path for local (non-Docker) dev.
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from ml.anomaly_detection.predict import MIN_TRANSACTIONS_FOR_DETECTION, AnomalyDetector
except ImportError:
    _repo_root = Path(__file__).resolve().parents[3]
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))
    from ml.anomaly_detection.predict import (  # noqa: E402
        MIN_TRANSACTIONS_FOR_DETECTION,
        AnomalyDetector,
    )

from app.models.anomaly import AnomalyDocument
from app.repositories.anomaly_repository import AnomalyRepository
from app.repositories.transaction_repository import TransactionRepository


def _severity(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"


# Loaded once at process start and reused across requests — sklearn/joblib
# deserialization isn't cheap enough to redo on every /detect call or CSV
# import (same rationale as app.services.categorization_service).
_detector = AnomalyDetector()


def get_anomaly_detector_status() -> tuple[bool, int | None]:
    """Used by GET /api/v1/ml/models to report registry status without
    requiring a full AnomalyDetectionService (which needs repositories).
    """
    return _detector.is_ready, _detector.active_version


class AnomalyDetectionService:
    def __init__(
        self, transaction_repo: TransactionRepository, anomaly_repo: AnomalyRepository
    ) -> None:
        self._transaction_repo = transaction_repo
        self._anomaly_repo = anomaly_repo
        self._detector = _detector

    def detect_for_user(self, user_id: str) -> dict:
        transactions = self._transaction_repo.list_all_for_user(user_id)

        if len(transactions) < MIN_TRANSACTIONS_FOR_DETECTION:
            return {
                "status": "insufficient_data",
                "message": (
                    f"Need at least {MIN_TRANSACTIONS_FOR_DETECTION} transactions for "
                    f"anomaly detection; you have {len(transactions)}."
                ),
                "anomalies_found": 0,
                "transactions_scanned": len(transactions),
            }

        payload = [
            {
                "amount": t.amount,
                "transaction_date": t.transaction_date,
                "category": t.category,
                "merchant": t.merchant,
                "description": t.description,
            }
            for t in transactions
        ]
        results = self._detector.detect(payload)
        assert results is not None  # length already checked above

        flag_updates = []
        anomaly_docs = []
        for txn, result in zip(transactions, results):
            flag_updates.append(
                {
                    "transaction_id": txn.id,
                    "is_anomaly": result.is_anomaly,
                    "anomaly_score": result.anomaly_score,
                }
            )
            if result.is_anomaly:
                anomaly_docs.append(
                    AnomalyDocument(
                        user_id=user_id,
                        transaction_id=txn.id,
                        anomaly_score=result.anomaly_score,
                        severity=_severity(result.anomaly_score),
                        reason=result.reason,
                    )
                )

        self._transaction_repo.update_anomaly_flags(flag_updates)
        self._anomaly_repo.replace_all_for_user(user_id, anomaly_docs)

        return {
            "status": "completed",
            "message": f"Scanned {len(transactions)} transactions, found {len(anomaly_docs)} anomalies.",
            "anomalies_found": len(anomaly_docs),
            "transactions_scanned": len(transactions),
        }
