"""Deterministic financial insights engine (master-prompt Rule 16: "Do not
use an external LLM API. Insights should be generated from actual MongoDB
[-derived] aggregation results, analytics, and ML results.").

Each `_rule_*` method looks at the user's already-fetched transaction
history (via TransactionRepository.list_all_for_user, the same
full-history-in-Python approach used by anomaly/recurring detection) and
either returns an InsightDocument or None if that pattern doesn't apply
yet (e.g. not enough months of history). A rule firing is never guaranteed
— a brand-new user with one month of data will simply get fewer insights,
not fabricated ones.

Aggregation here is done in pandas over a full history fetch rather than a
MongoDB aggregation pipeline, for the same reason the anomaly/recurring
services do this: at this dataset scale (one user's transactions) it's
simpler and just as fast, and keeps insight logic in one place instead of
splitting it between Mongo pipeline stages and Python post-processing.
A high-volume production deployment could push the group-by/sum steps into
a $group aggregation stage instead — the rule logic below would be
unchanged, only where the summing happens.
"""

import pandas as pd

from app.models.insight import InsightDocument
from app.repositories.insight_repository import InsightRepository
from app.repositories.recurring_repository import RecurringRepository
from app.repositories.transaction_repository import TransactionRepository

# Minimum baseline spend in a category before a month-over-month percentage
# change is considered meaningful — otherwise a category that went from ₹10
# to ₹50 would report a headline-grabbing "400% increase."
MIN_CATEGORY_BASELINE = 100.0
CATEGORY_INCREASE_THRESHOLD_PCT = 15.0
CATEGORY_SHARE_THRESHOLD_PCT = 15.0
WEEKEND_SPENDING_MULTIPLIER = 1.2


def _transactions_to_frame(transactions) -> pd.DataFrame:
    if not transactions:
        return pd.DataFrame(
            columns=["transaction_date", "amount", "category", "description", "merchant"]
        )
    df = pd.DataFrame(
        [
            {
                "transaction_date": t.transaction_date,
                "amount": t.amount,
                "category": t.category,
                "description": t.description,
                "merchant": t.merchant,
            }
            for t in transactions
            if t.transaction_type == "debit"
        ]
    )
    if df.empty:
        return df
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    df["month"] = df["transaction_date"].dt.to_period("M")
    df["date"] = df["transaction_date"].dt.date
    return df


class InsightsEngine:
    def __init__(
        self,
        transaction_repo: TransactionRepository,
        recurring_repo: RecurringRepository,
        insight_repo: InsightRepository,
    ) -> None:
        self._transaction_repo = transaction_repo
        self._recurring_repo = recurring_repo
        self._insight_repo = insight_repo

    def generate_for_user(self, user_id: str) -> dict:
        insights = self.generate(user_id)
        self._insight_repo.replace_all_for_user(user_id, insights)
        return {
            "status": "completed",
            "message": f"Generated {len(insights)} insight(s).",
            "insights_found": len(insights),
        }

    def generate(self, user_id: str) -> list[InsightDocument]:
        transactions = self._transaction_repo.list_all_for_user(user_id)
        df = _transactions_to_frame(transactions)

        insights: list[InsightDocument] = []
        for rule in (
            self._rule_category_increase,
            self._rule_category_share,
            self._rule_weekend_spending,
            self._rule_largest_expense,
            self._rule_consecutive_monthly_increase,
        ):
            result = rule(df)
            if result is not None:
                insights.append(InsightDocument(user_id=user_id, type=result[0], message=result[1]))

        recurring_insight = self._rule_recurring_count(user_id)
        if recurring_insight is not None:
            insights.append(
                InsightDocument(user_id=user_id, type=recurring_insight[0], message=recurring_insight[1])
            )

        return insights

    def _rule_category_increase(self, df: pd.DataFrame) -> tuple[str, str] | None:
        months = sorted(df["month"].unique()) if not df.empty else []
        if len(months) < 2:
            return None
        current_month, previous_month = months[-1], months[-2]

        current = df[df["month"] == current_month].groupby("category")["amount"].sum()
        previous = df[df["month"] == previous_month].groupby("category")["amount"].sum()

        best_category, best_pct = None, 0.0
        for category, prev_amount in previous.items():
            if prev_amount < MIN_CATEGORY_BASELINE:
                continue
            current_amount = current.get(category, 0.0)
            pct_change = (current_amount - prev_amount) / prev_amount * 100
            if pct_change > best_pct:
                best_category, best_pct = category, pct_change

        if best_category is None or best_pct < CATEGORY_INCREASE_THRESHOLD_PCT:
            return None
        return (
            "category_increase",
            f"Your {best_category} spending increased {best_pct:.0f}% compared with last month.",
        )

    def _rule_category_share(self, df: pd.DataFrame) -> tuple[str, str] | None:
        if df.empty:
            return None
        current_month = df["month"].max()
        current = df[df["month"] == current_month].groupby("category")["amount"].sum()
        total = current.sum()
        if total <= 0:
            return None

        top_category = current.idxmax()
        share_pct = current[top_category] / total * 100
        if share_pct < CATEGORY_SHARE_THRESHOLD_PCT:
            return None
        return (
            "category_share",
            f"{top_category} represents {share_pct:.0f}% of your monthly expenses.",
        )

    def _rule_weekend_spending(self, df: pd.DataFrame) -> tuple[str, str] | None:
        if df.empty:
            return None
        current_month = df["month"].max()
        month_df = df[df["month"] == current_month].copy()
        if month_df.empty:
            return None
        month_df["is_weekend"] = month_df["transaction_date"].dt.dayofweek >= 5

        weekend_dates = month_df.loc[month_df["is_weekend"], "date"].nunique()
        weekday_dates = month_df.loc[~month_df["is_weekend"], "date"].nunique()
        if weekend_dates == 0 or weekday_dates == 0:
            return None

        weekend_avg = month_df.loc[month_df["is_weekend"], "amount"].sum() / weekend_dates
        weekday_avg = month_df.loc[~month_df["is_weekend"], "amount"].sum() / weekday_dates
        if weekday_avg <= 0 or weekend_avg < weekday_avg * WEEKEND_SPENDING_MULTIPLIER:
            return None

        return (
            "weekend_spending",
            "You tend to spend more per day on weekends than on weekdays this month.",
        )

    def _rule_largest_expense(self, df: pd.DataFrame) -> tuple[str, str] | None:
        if df.empty:
            return None
        current_month = df["month"].max()
        month_df = df[df["month"] == current_month]
        if month_df.empty:
            return None

        top = month_df.loc[month_df["amount"].idxmax()]
        label = top["merchant"] or top["description"]
        return (
            "largest_expense",
            f"Your largest expense this month was {label} at {top['amount']:.0f}.",
        )

    def _rule_consecutive_monthly_increase(self, df: pd.DataFrame) -> tuple[str, str] | None:
        months = sorted(df["month"].unique()) if not df.empty else []
        if len(months) < 4:
            return None
        last_four = months[-4:]
        totals = [df[df["month"] == m]["amount"].sum() for m in last_four]
        increasing = all(totals[i] < totals[i + 1] for i in range(len(totals) - 1))
        if not increasing:
            return None
        return (
            "consecutive_increase",
            "Your monthly spending has increased for three consecutive months.",
        )

    def _rule_recurring_count(self, user_id: str) -> tuple[str, str] | None:
        items, total = self._recurring_repo.list_for_user(user_id, skip=0, limit=1)
        if total == 0:
            return None
        plural = "s" if total != 1 else ""
        return ("recurring_count", f"You have {total} recurring payment{plural} detected.")
