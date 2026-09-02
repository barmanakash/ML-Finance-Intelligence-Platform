"""Demo seed script (master-prompt Rule 39, "Demo Mode"):
create a demo user, import realistic synthetic transactions, and let the
existing import pipeline (categorize -> detect anomalies -> detect
recurring -> forecast -> generate insights) populate everything else —
exactly the steps Rule 39 lists, all triggered by one CSV import because
app.services.transaction_import_service.TransactionImportService already
runs the full pipeline after every import (see Phases 4-8).

Usage:
    python scripts/seed.py
    python scripts/seed.py --email demo@example.com --password Demo1234!
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
for path in (REPO_ROOT, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from pymongo import MongoClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.models.user import UserDocument  # noqa: E402
from app.repositories.anomaly_repository import AnomalyRepository  # noqa: E402
from app.repositories.category_repository import CategoryRepository  # noqa: E402
from app.repositories.forecast_repository import ForecastRepository  # noqa: E402
from app.repositories.insight_repository import InsightRepository  # noqa: E402
from app.repositories.recurring_repository import RecurringRepository  # noqa: E402
from app.repositories.transaction_import_repository import TransactionImportRepository  # noqa: E402
from app.repositories.transaction_repository import TransactionRepository  # noqa: E402
from app.repositories.user_repository import UserRepository  # noqa: E402
from app.services.anomaly_detection_service import AnomalyDetectionService  # noqa: E402
from app.services.forecast_service import ForecastService  # noqa: E402
from app.services.insights_engine import InsightsEngine  # noqa: E402
from app.services.recurring_detection_service import RecurringDetectionService  # noqa: E402
from app.services.transaction_import_service import TransactionImportService  # noqa: E402
from app.utils.security import hash_password  # noqa: E402

from scripts.generate_sample_data import generate_transactions, transactions_to_csv_bytes  # noqa: E402


def seed(email: str, password: str, full_name: str, num_days: int) -> None:
    settings = get_settings()
    client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    db = client[settings.mongodb_database]
    print(f"Connected to MongoDB database: {db.name}")

    CategoryRepository(db).ensure_defaults_seeded()
    print("Default categories ensured.")

    user_repo = UserRepository(db)
    existing_user = user_repo.get_by_email(email)
    if existing_user is not None:
        print(f"Demo user {email} already exists (id={existing_user.id}); reusing it.")
        user = existing_user
    else:
        user = user_repo.create(
            UserDocument(email=email, hashed_password=hash_password(password), full_name=full_name)
        )
        print(f"Created demo user {email} (id={user.id}).")

    rows = generate_transactions(num_days=num_days, seed=42)
    csv_bytes = transactions_to_csv_bytes(rows)
    print(f"Generated {len(rows)} synthetic transactions spanning ~{num_days} days.")

    import_service = TransactionImportService(
        TransactionRepository(db),
        TransactionImportRepository(db),
        AnomalyDetectionService(TransactionRepository(db), AnomalyRepository(db)),
        RecurringDetectionService(TransactionRepository(db), RecurringRepository(db)),
        ForecastService(TransactionRepository(db), ForecastRepository(db)),
        InsightsEngine(TransactionRepository(db), RecurringRepository(db), InsightRepository(db)),
    )

    try:
        import_record = import_service.import_csv(user.id, "seed_demo_transactions.csv", csv_bytes)
    except Exception as exc:  # a re-run with identical data would hit the duplicate-file guard
        print(f"Import skipped: {exc}")
        print("(This is expected if you've already run `make seed` — the same synthetic file hashes identically.)")
        return

    print(
        f"Import complete: {import_record.imported_rows} transactions imported, "
        f"{import_record.failed_rows} rows failed (status={import_record.status})."
    )
    print()
    print("Demo data is ready. Log in with:")
    print(f"  email:    {email}")
    print(f"  password: {password}")
    print()
    print(
        "Note: categorization/anomaly/forecast results will be more meaningful once you've "
        "trained the models (`make generate-data && make train`); until then, categorization "
        "falls back to 'Uncategorized' and anomaly/forecast endpoints report as not-yet-available."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed a demo user with realistic transaction history")
    parser.add_argument("--email", default="demo@example.com")
    parser.add_argument("--password", default="DemoPass123!")
    parser.add_argument("--full-name", default="Demo User")
    parser.add_argument("--days", type=int, default=180)
    args = parser.parse_args()

    seed(args.email, args.password, args.full_name, args.days)
