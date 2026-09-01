"""MongoDB document schema for the `insights` collection.

One document per generated insight message. Like anomalies/recurring, the
whole collection is replaced wholesale for a user each time insights
re-generate (see InsightRepository.replace_all_for_user and
InsightsEngine.generate_for_user) — insights are a snapshot of "what's
true about your spending right now," not a running log.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class InsightDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    user_id: str
    type: str  # e.g. "category_increase", "weekend_spending", "largest_expense"
    message: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
