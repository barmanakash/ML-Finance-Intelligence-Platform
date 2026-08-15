"""Synthetic per-user transaction-history generator for anomaly-detection
training.

Simulates several synthetic users, each with a routine spending pattern
(a handful of regular merchants per category, amounts drawn from a normal
distribution around a per-merchant mean), then injects a small number of
anomalies per user — either an amount far outside that user's usual range
for a merchant/category, or a one-off transaction with a merchant they've
never used before.

The injected-anomaly label (`is_synthetic_anomaly`) is kept ONLY for
offline evaluation (a sanity check on precision/recall against known
outliers). It is never passed to IsolationForest.fit(), which is
unsupervised — training never sees this column.

Usage:
    python -m ml.datasets.generate_anomaly_dataset
"""

import random
from pathlib import Path

import numpy as np
import pandas as pd

from ml.common.config import DATA_DIR

random.seed(7)
np.random.seed(7)

# category -> [(merchant, mean_amount, std_amount), ...]
ROUTINE_MERCHANTS: dict[str, list[tuple[str, float, float]]] = {
    "Food": [("SWIGGY", 300, 80), ("ZOMATO", 350, 90), ("STARBUCKS", 250, 60)],
    "Groceries": [("BIGBASKET", 1200, 300), ("DMART", 900, 250)],
    "Transportation": [("UBER", 200, 70), ("OLA CABS", 180, 60)],
    "Shopping": [("AMAZON", 1500, 900), ("FLIPKART", 1300, 800)],
    "Entertainment": [("BOOKMYSHOW", 400, 120), ("SPOTIFY PREMIUM", 199, 5)],
    "Bills": [("ELECTRICITY BILL PAYMENT", 2200, 500)],
    "Utilities": [("JIO RECHARGE", 399, 50)],
    "Subscription": [("NETFLIX SUBSCRIPTION", 649, 5)],
}

RARE_MERCHANTS = [
    "LUXURY WATCH STORE", "ELECTRONICS MEGA MART", "OVERSEAS TRANSFER", "JEWELLERY EMPORIUM",
]

N_USERS = 40
TRANSACTIONS_PER_USER = 60
ANOMALY_RATE = 0.05


def _gen_user_transactions(user_id: str, start_date: pd.Timestamp) -> list[dict]:
    rows = []
    categories = list(ROUTINE_MERCHANTS.keys())

    for _ in range(TRANSACTIONS_PER_USER):
        category = random.choice(categories)
        merchant, mean_amt, std_amt = random.choice(ROUTINE_MERCHANTS[category])
        amount = max(10.0, float(np.random.normal(mean_amt, std_amt)))
        date = start_date + pd.Timedelta(days=random.randint(0, 89))
        rows.append(
            {
                "user_id": user_id,
                "transaction_date": date,
                "category": category,
                "merchant": merchant,
                "amount": round(amount, 2),
                "is_synthetic_anomaly": 0,
            }
        )

    n_anomalies = max(1, int(TRANSACTIONS_PER_USER * ANOMALY_RATE))
    for _ in range(n_anomalies):
        if random.random() < 0.5:
            # Amount spike on a merchant/category the user actually uses.
            category = random.choice(categories)
            merchant, mean_amt, _std_amt = random.choice(ROUTINE_MERCHANTS[category])
            amount = mean_amt * random.uniform(6, 15)
        else:
            # A one-off transaction with a merchant never seen before.
            category = "Other"
            merchant = random.choice(RARE_MERCHANTS)
            amount = random.uniform(15000, 60000)
        date = start_date + pd.Timedelta(days=random.randint(0, 89))
        rows.append(
            {
                "user_id": user_id,
                "transaction_date": date,
                "category": category,
                "merchant": merchant,
                "amount": round(amount, 2),
                "is_synthetic_anomaly": 1,
            }
        )
    return rows


def generate(output_path: Path) -> int:
    start_date = pd.Timestamp("2026-01-01")
    all_rows = []
    for u in range(N_USERS):
        all_rows.extend(_gen_user_transactions(f"synthetic-user-{u}", start_date))

    df = pd.DataFrame(all_rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return len(df)


if __name__ == "__main__":
    output = DATA_DIR / "training" / "anomaly_dataset.csv"
    count = generate(output)
    print(f"Generated {count} synthetic transactions across {N_USERS} users -> {output}")
