"""Synthetic daily-spend time-series generator for forecasting.

Each synthetic user gets a continuous daily total-spend series (every
calendar day has a value, including 0.0 on no-spend days) with:
  - a base daily spend level,
  - weekly seasonality (weekends spend more, matching real discretionary
    spending patterns),
  - a slow upward or downward trend (so linear regression sometimes wins,
    sometimes doesn't — the point of ml.forecasting.train comparing
    methods rather than assuming one is always best),
  - Gaussian noise.

Usage:
    python -m ml.datasets.generate_forecast_dataset
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

from ml.common.config import DATA_DIR

random.seed(42)

NUM_USERS = 20
DAYS_PER_USER = 200


def generate(output_path: Path) -> int:
    rows = []

    for user_idx in range(NUM_USERS):
        user_id = f"synthetic-forecast-user-{user_idx}"
        start_date = datetime(2025, 6, 1)
        base_level = random.uniform(300, 900)
        trend_per_day = random.uniform(-0.5, 1.5)
        weekend_multiplier = random.uniform(1.2, 1.8)
        noise_std = base_level * 0.2

        for day_offset in range(DAYS_PER_USER):
            current_date = start_date + timedelta(days=day_offset)
            level = base_level + trend_per_day * day_offset
            if current_date.weekday() >= 5:  # Saturday/Sunday
                level *= weekend_multiplier
            amount = max(0.0, random.gauss(level, noise_std))

            rows.append(
                {
                    "user_id": user_id,
                    "date": current_date.strftime("%Y-%m-%d"),
                    "daily_amount": round(amount, 2),
                }
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["user_id", "date", "daily_amount"])
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    output = DATA_DIR / "training" / "forecast_dataset.csv"
    count = generate(output)
    print(f"Generated {count} daily-spend rows across {NUM_USERS} users -> {output}")
