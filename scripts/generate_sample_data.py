"""Synthetic bank-export CSV generator (master-prompt Rule 38: "create a
synthetic transaction generator... Generate: multiple users, different
merchants, categories, recurring payments, normal transactions, unusual
transactions, income, expenses, seasonal patterns.").

This is deliberately separate from the ml/datasets/generate_*.py scripts:
those produce *labeled training data* for a specific model (description ->
category, or a daily-spend time series). This script produces a realistic
*bank statement CSV* in the exact shape a user would upload through
POST /api/v1/imports — no labels, just date/description/amount/type — so
it can exercise the whole pipeline (import -> categorize -> detect
anomalies -> detect recurring -> forecast -> insights) end to end, which is
exactly what scripts/seed.py uses it for.

Usage:
    python -m scripts.generate_sample_data                       # writes 3 users' CSVs
    python -m scripts.generate_sample_data --users 5 --days 240
"""

from __future__ import annotations

import argparse
import csv as csv_module
import io
import random
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "sample"

# (description, category, min_amount, max_amount) — description text
# deliberately mirrors the vocabulary ml/datasets/generate_categorization_dataset.py
# trains on, so the categorizer has a realistic shot at labeling these
# correctly rather than falling back to "Uncategorized".
DAILY_MERCHANTS: list[tuple[str, str, float, float]] = [
    ("SWIGGY ORDER", "Food", 150, 650),
    ("ZOMATO ORDER", "Food", 150, 700),
    ("MCDONALDS", "Food", 120, 450),
    ("BIGBASKET GROCERY", "Groceries", 400, 2200),
    ("DMART SUPERMARKET", "Groceries", 300, 1800),
    ("UBER TRIP", "Transportation", 80, 450),
    ("OLA CABS", "Transportation", 80, 400),
    ("AMAZON.IN", "Shopping", 300, 4500),
    ("FLIPKART", "Shopping", 250, 3800),
    ("MYNTRA FASHION", "Shopping", 400, 2500),
    ("BOOKMYSHOW", "Entertainment", 200, 900),
    ("APOLLO PHARMACY", "Healthcare", 150, 1200),
]

OCCASIONAL_MERCHANTS: list[tuple[str, str, float, float]] = [
    ("MAKEMYTRIP FLIGHT", "Travel", 3500, 12000),
    ("IRCTC TRAIN BOOKING", "Travel", 500, 2500),
    ("UDEMY COURSE", "Education", 400, 3000),
    ("ZERODHA INVESTMENT", "Investment", 1000, 10000),
    ("ATM CASH WITHDRAWAL", "Cash Withdrawal", 1000, 5000),
    ("UPI TRANSFER TO FRIEND", "Transfer", 200, 3000),
]

# (description, category, amount) — fixed monthly recurring items.
MONTHLY_SUBSCRIPTIONS: list[tuple[str, str, float]] = [
    ("NETFLIX SUBSCRIPTION", "Subscription", 649.0),
    ("SPOTIFY PREMIUM", "Subscription", 119.0),
    ("AMAZON PRIME MEMBERSHIP", "Subscription", 179.0),
]
MONTHLY_BILLS: list[tuple[str, str, float, float]] = [
    ("ELECTRICITY BOARD BILL", "Bills", 800, 2500),
    ("JIO FIBER BROADBAND", "Utilities", 799, 1500),
]

RENT_DESCRIPTION = ("MONTHLY RENT PAYMENT", "Rent", 12000, 35000)
SALARY_DESCRIPTION = "SALARY CREDIT"

ANOMALY_MERCHANTS = [
    ("AMAZON.IN - LAPTOP PURCHASE", "Shopping", 55000, 95000),
    ("APOLLO HOSPITALS EMERGENCY", "Healthcare", 25000, 60000),
    ("MAKEMYTRIP FLIGHT - INTERNATIONAL", "Travel", 45000, 80000),
]


def _random_day_in_month(year: int, month: int, rng: random.Random) -> date:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    days_in_month = (next_month - date(year, month, 1)).days
    return date(year, month, rng.randint(1, days_in_month))


def generate_transactions(
    *, num_days: int = 180, seed: int | None = None, anomaly_count: int = 2
) -> list[dict]:
    """Returns a list of {date, description, amount, type} dicts covering
    `num_days` days ending today, with monthly salary/rent/subscriptions,
    randomized day-to-day spending, and a handful of injected anomalies.
    """
    rng = random.Random(seed)
    start_date = date.today() - timedelta(days=num_days)
    rows: list[dict] = []

    monthly_income = round(rng.uniform(45000, 90000), 2)
    rent_amount = round(rng.uniform(*RENT_DESCRIPTION[2:4]), 2)

    months_seen: set[tuple[int, int]] = set()
    for day_offset in range(num_days):
        current = start_date + timedelta(days=day_offset)
        month_key = (current.year, current.month)

        if month_key not in months_seen and current.day <= 5:
            months_seen.add(month_key)
            rows.append(
                {"date": current.isoformat(), "description": SALARY_DESCRIPTION, "amount": monthly_income, "type": "credit"}
            )
            rows.append(
                {
                    "date": (current + timedelta(days=rng.randint(0, 2))).isoformat(),
                    "description": RENT_DESCRIPTION[0],
                    "amount": rent_amount,
                    "type": "debit",
                }
            )
            for desc, _cat, amount in MONTHLY_SUBSCRIPTIONS:
                rows.append(
                    {
                        "date": (current + timedelta(days=rng.randint(0, 4))).isoformat(),
                        "description": desc,
                        "amount": amount,
                        "type": "debit",
                    }
                )
            for desc, _cat, lo, hi in MONTHLY_BILLS:
                rows.append(
                    {
                        "date": (current + timedelta(days=rng.randint(2, 10))).isoformat(),
                        "description": desc,
                        "amount": round(rng.uniform(lo, hi), 2),
                        "type": "debit",
                    }
                )

        # Weekend spending bump matches the seasonality baked into
        # ml/datasets/generate_forecast_dataset.py, so a seeded demo user's
        # own forecast/insights ("you spend more on weekends") is coherent.
        is_weekend = current.weekday() >= 5
        num_daily_txns = rng.choices([0, 1, 2, 3], weights=[10, 35, 35, 20])[0]
        if is_weekend:
            num_daily_txns += rng.choice([0, 1])

        for _ in range(num_daily_txns):
            desc, _cat, lo, hi = rng.choice(DAILY_MERCHANTS)
            rows.append(
                {"date": current.isoformat(), "description": desc, "amount": round(rng.uniform(lo, hi), 2), "type": "debit"}
            )

        if rng.random() < 0.05:
            desc, _cat, lo, hi = rng.choice(OCCASIONAL_MERCHANTS)
            rows.append(
                {"date": current.isoformat(), "description": desc, "amount": round(rng.uniform(lo, hi), 2), "type": "debit"}
            )

    for _ in range(anomaly_count):
        desc, _cat, lo, hi = rng.choice(ANOMALY_MERCHANTS)
        anomaly_date = start_date + timedelta(days=rng.randint(10, num_days - 1))
        rows.append(
            {"date": anomaly_date.isoformat(), "description": desc, "amount": round(rng.uniform(lo, hi), 2), "type": "debit"}
        )

    rows.sort(key=lambda r: r["date"])
    return rows


def transactions_to_csv_bytes(rows: list[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv_module.DictWriter(buffer, fieldnames=["date", "description", "amount", "type"])
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def generate(num_users: int, num_days: int, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for user_idx in range(num_users):
        rows = generate_transactions(num_days=num_days, seed=1000 + user_idx)
        csv_bytes = transactions_to_csv_bytes(rows)
        path = output_dir / f"demo_user_{user_idx + 1}_transactions.csv"
        path.write_bytes(csv_bytes)
        written.append(path)
    return written


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic bank-export CSVs for demo/testing")
    parser.add_argument("--users", type=int, default=3)
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    paths = generate(args.users, args.days, args.output_dir)
    for path in paths:
        print(f"Generated {path}")
