import os
import logging
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, OperationFailure

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database():
    """Get MongoDB database instance."""
    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("MONGODB_DATABASE", "finance_ml")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        return client[db_name]
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

def create_indexes():
    """Create all documented MongoDB indexes idempotently."""
    db = get_database()
    logger.info(f"Connected to database: {db.name}")

    indexes_to_create = [
        # users
        ("users", [("email", ASCENDING)], {"unique": True}, "Unique email for users"),
        # transactions
        ("transactions", [("user_id", ASCENDING), ("transaction_date", DESCENDING)], {}, "Query transactions by user and date"),
        ("transactions", [("user_id", ASCENDING), ("category", ASCENDING)], {}, "Query transactions by user and category"),
        ("transactions", [("user_id", ASCENDING), ("merchant", ASCENDING)], {}, "Query transactions by user and merchant"),
        ("transactions", [("user_id", ASCENDING), ("is_anomaly", ASCENDING)], {}, "Query anomalous transactions by user"),
        ("transactions", [("import_id", ASCENDING)], {}, "Query transactions by import batch"),
        # transaction_imports
        ("transaction_imports", [("user_id", ASCENDING), ("created_at", DESCENDING)], {}, "List imports by user"),
        ("transaction_imports", [("user_id", ASCENDING), ("file_hash", ASCENDING)], {"unique": True}, "Prevent duplicate file imports"),
        # categories
        ("categories", [("name", ASCENDING), ("user_id", ASCENDING)], {"unique": True}, "Unique category name per user (null user for system defaults)"),
        # anomalies
        ("anomalies", [("user_id", ASCENDING), ("created_at", DESCENDING)], {}, "List anomalies by user"),
        ("anomalies", [("transaction_id", ASCENDING)], {"unique": True}, "One anomaly record per transaction"),
        # recurring_transactions
        ("recurring_transactions", [("user_id", ASCENDING), ("merchant", ASCENDING)], {"unique": True}, "Unique recurring pattern per merchant and user"),
        # expense_forecasts
        ("expense_forecasts", [("user_id", ASCENDING), ("period", ASCENDING)], {}, "Query forecasts by user and period"),
        # ml_models
        ("ml_models", [("name", ASCENDING), ("version", DESCENDING)], {"unique": True}, "Unique model version"),
        ("ml_models", [("name", ASCENDING), ("status", ASCENDING)], {}, "Query active models by name"),
        # insights
        ("insights", [("user_id", ASCENDING), ("created_at", DESCENDING)], {}, "List insights by user"),
        # audit_logs
        ("audit_logs", [("user_id", ASCENDING), ("created_at", DESCENDING)], {}, "List audit logs by user"),
        ("audit_logs", [("created_at", ASCENDING)], {"expireAfterSeconds": 90 * 24 * 60 * 60}, "TTL index: 90 days retention"),
    ]

    for coll_name, keys, kwargs, description in indexes_to_create:
        try:
            collection = db[coll_name]
            # Ensure unique constraints properly handle existing non-unique data if possible,
            # but ideally this runs on an empty/clean db or handles errors gracefully
            name = collection.create_index(keys, **kwargs)
            logger.info(f"Created index '{name}' on '{coll_name}': {description}")
        except OperationFailure as e:
            logger.warning(f"Index creation failed on '{coll_name}' with keys {keys}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating index on '{coll_name}': {e}")

    logger.info("Index creation process finished.")

if __name__ == "__main__":
    create_indexes()
