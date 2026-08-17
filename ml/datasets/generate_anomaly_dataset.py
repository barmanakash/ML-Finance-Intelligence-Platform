"""Synthetic single-user transaction history with injected anomalies, used
ONLY to evaluate the anomaly-detection pipeline's mechanics (see
ml/anomaly_detection/evaluate.py). Real anomaly detection at serving time
never touches this file — it fits on each user's actual transaction history
on demand (see ml/anomaly_detection/predict.py).

There is no verified-fraud ground truth available for a personal project
like this, so "injected anomaly" here means a transaction we deliberately
built with characteristics a human would call unusual (an extreme amount
spike, or a brand-new/unfamiliar merchant) — not confirmed fraud. Treat the
resulting precision/recall as a sanity check that the pipeline catches the
kinds of patterns it's designed to catch, not a real-world accuracy claim.

Usage:
    python -m ml.datasets.generate_anomaly_dataset
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

from ml.common.config import DATA_DIR

random.seed(7)

# (category, merchant, normal_amount_low, normal_amount_high)
NORMAL_PATTERNS = [
    ("Food", "SWIGGY", 200, 600),
    ("Food", "ZOMATO", 150, 500),
    ("Groceries", "BIGBASKET", 800, 2500),
    ("Transportation", "UBER", 100, 450),
    ("Shopping", "AMAZON", 300, 3000),
    ("Utilities", "AIRTEL POSTPAID", 400, 900),
    ("Entertainment", "NETFLIX SUBSCRIPTION", 500, 650),
    ("Bills", "ELECTRICITY BILL PAYMENT", 800, 2200),
]

ANOMALY_MERCHANTS = [
    "UNKNOWN OVERSEAS MERCHANT",
    "LUXURY WATCH BOUTIQUE",
    "CASINO PAYMENT GATEWAY",
]


def generate(output_path: Path, num_normal: int = 150, num_anomalies: int = 12) -> int:
    rows = []
    start_date = datetime(2026, 1, 1)

    for _ in range(num_normal):
        category, merchant, lo, hi = random.choice(NORMAL_PATTERNS)
        amount = round(random.uniform(lo, hi), 2)
        date = start_date + timedelta(days=random.randint(0, 180))
        rows.append(
            {
                "transaction_date": date.strftime("%Y-%m-%d"),
                "description": merchant,
                "merchant": merchant,
                "category": category,
                "amount": amount,
                "is_injected_anomaly": 0,
            }
        )

    for i in range(num_anomalies):
        # Two flavors: an extreme amount spike on an otherwise-normal
        # merchant, or a brand-new/unusual merchant entirely.
        if i % 2 == 0:
            category, merchant, _lo, hi = random.choice(NORMAL_PATTERNS)
            amount = round(hi * random.uniform(8, 20), 2)
        else:
            merchant = random.choice(ANOMALY_MERCHANTS)
            category = "Other"
            amount = round(random.uniform(15000, 50000), 2)
        date = start_date + timedelta(days=random.randint(0, 180))
        rows.append(
            {
                "transaction_date": date.strftime("%Y-%m-%d"),
                "description": merchant,
                "merchant": merchant,
                "category": category,
                "amount": amount,
                "is_injected_anomaly": 1,
            }
        )

    random.shuffle(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["transaction_date", "description", "merchant", "category", "amount", "is_injected_anomaly"]
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    output = DATA_DIR / "training" / "anomaly_eval_dataset.csv"
    count = generate(output)
    print(
        f"Generated {count} synthetic transactions "
        f"({12} injected anomalies) -> {output}"
    )
