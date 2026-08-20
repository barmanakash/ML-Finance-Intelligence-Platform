"""Synthetic transaction-history generator for anomaly detection.

Each synthetic user gets a chronological sequence of "normal" transactions
(small amount variance around a per-merchant baseline) spanning several
months. A small fraction of transactions are deliberately injected as
anomalies (large amount spikes on a known merchant, or a brand-new,
unusually large merchant) so ml/anomaly_detection/evaluate.py has something
to check precision/recall against.

IsolationForest itself is unsupervised and never sees the
`is_injected_anomaly` label during training — see
ml/anomaly_detection/train.py. This label exists purely for evaluation, per
master-prompt Rule 43: unsupervised anomaly detection has no real-world
ground truth, so this evaluation is illustrative, not a performance
guarantee on real bank data.

Usage:
    python -m ml.datasets.generate_anomaly_dataset
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

from ml.common.config import DATA_DIR

random.seed(42)

# (merchant, category) -> typical amount for that merchant, in the same
# generic-brand-name style as ml/datasets/generate_categorization_dataset.py.
MERCHANT_CATEGORY_BASE_AMOUNT: dict[tuple[str, str], float] = {
    ("SWIGGY", "Food"): 350,
    ("ZOMATO", "Food"): 400,
    ("STARBUCKS", "Food"): 250,
    ("BIGBASKET", "Groceries"): 1500,
    ("DMART", "Groceries"): 2000,
    ("UBER", "Transportation"): 200,
    ("OLA CABS", "Transportation"): 180,
    ("INDIAN OIL PETROL", "Transportation"): 1000,
    ("AMAZON", "Shopping"): 1200,
    ("FLIPKART", "Shopping"): 1000,
    ("MYNTRA", "Shopping"): 1500,
    ("NETFLIX SUBSCRIPTION", "Subscription"): 649,
    ("AIRTEL POSTPAID", "Utilities"): 599,
    ("ELECTRICITY BILL PAYMENT", "Bills"): 2200,
    ("HOUSE RENT NEFT", "Rent"): 15000,
    ("SALARY CREDIT", "Salary"): 65000,
    ("ZERODHA", "Investment"): 5000,
    ("APOLLO PHARMACY", "Healthcare"): 450,
}

# Merchants that never appear in a user's "normal" history — used for the
# new-merchant-with-large-amount anomaly type.
NEW_MERCHANT_POOL: list[tuple[str, str]] = [
    ("UNKNOWN ELECTRONICS STORE", "Shopping"),
    ("LUXURY WATCH BOUTIQUE", "Shopping"),
    ("FOREIGN CURRENCY EXCHANGE", "Other"),
]

TRANSACTIONS_PER_USER = 120
NUM_USERS = 15
ANOMALY_RATE = 0.04


def generate(output_path: Path) -> int:
    rows = []
    merchants = list(MERCHANT_CATEGORY_BASE_AMOUNT.keys())

    for user_idx in range(NUM_USERS):
        user_id = f"synthetic-user-{user_idx}"
        current_date = datetime(2025, 1, 1) + timedelta(days=random.randint(0, 30))

        for _ in range(TRANSACTIONS_PER_USER):
            current_date += timedelta(days=random.randint(0, 3))
            is_anomaly = random.random() < ANOMALY_RATE

            if is_anomaly and random.random() < 0.5:
                merchant, category = random.choice(NEW_MERCHANT_POOL)
                amount = round(random.uniform(15000, 60000), 2)
            elif is_anomaly:
                merchant, category = random.choice(merchants)
                base = MERCHANT_CATEGORY_BASE_AMOUNT[(merchant, category)]
                amount = round(base * random.uniform(6, 12), 2)
            else:
                merchant, category = random.choice(merchants)
                base = MERCHANT_CATEGORY_BASE_AMOUNT[(merchant, category)]
                amount = round(max(10.0, random.gauss(base, base * 0.15)), 2)

            rows.append(
                {
                    "user_id": user_id,
                    "date": current_date.strftime("%Y-%m-%d"),
                    "description": merchant,
                    "merchant": merchant,
                    "category": category,
                    "amount": amount,
                    "is_injected_anomaly": int(is_anomaly),
                }
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "user_id", "date", "description", "merchant",
                "category", "amount", "is_injected_anomaly",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    output = DATA_DIR / "training" / "anomaly_dataset.csv"
    count = generate(output)
    print(f"Generated {count} synthetic transactions across {NUM_USERS} users -> {output}")
