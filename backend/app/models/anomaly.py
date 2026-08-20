"""MongoDB document schema for the `anomalies` collection.

One document per flagged transaction. The whole collection is replaced
wholesale for a user each time anomaly detection re-runs (see
AnomalyRepository.replace_all_for_user and
app.services.anomaly_detection_service.AnomalyDetectionService) since
detection always re-scores a user's entire history at once rather than
incrementally.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class AnomalyDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    user_id: str
    transaction_id: str
    anomaly_score: float
    severity: str  # "low" | "medium" | "high"
    reason: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
