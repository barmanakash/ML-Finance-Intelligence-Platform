import os
import logging
from pymongo import MongoClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_CATEGORIES = [
    "Food", "Groceries", "Transportation", "Travel", "Shopping", 
    "Entertainment", "Bills", "Utilities", "Healthcare", "Education", 
    "Rent", "Salary", "Investment", "Transfer", "Subscription", 
    "Cash Withdrawal", "Other"
]

def get_database():
    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("MONGODB_DATABASE", "finance_ml")
    client = MongoClient(uri)
    return client[db_name]

def run_initial_setup():
    """Initial database setup including collections and default data."""
    db = get_database()
    logger.info(f"Connected to database: {db.name}")

    # Create system categories if they don't exist
    categories_coll = db["categories"]
    
    for cat_name in DEFAULT_CATEGORIES:
        # user_id = null for system defaults
        categories_coll.update_one(
            {"name": cat_name, "user_id": None},
            {"$setOnInsert": {"name": cat_name, "user_id": None, "is_system": True}},
            upsert=True
        )
    
    logger.info(f"Ensured {len(DEFAULT_CATEGORIES)} system categories exist.")
    
    # Import and run create_indexes
    try:
        from .create_indexes import create_indexes
        create_indexes()
    except ImportError:
        # Fallback if imported directly from scripts
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        try:
            from create_indexes import create_indexes
            create_indexes()
        except ImportError as e:
            logger.error(f"Could not import create_indexes: {e}")

    logger.info("v001_initial_setup complete.")

if __name__ == "__main__":
    run_initial_setup()
