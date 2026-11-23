"""MongoDB connection helpers for ProjectPilot AI."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.data_loader import load_projects, normalize_project_dataframe


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    """Load simple KEY=VALUE pairs from .env without adding a dependency."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        cleaned_line = line.strip()
        if not cleaned_line or cleaned_line.startswith("#") or "=" not in cleaned_line:
            continue

        key, value = cleaned_line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "project_data")
PROJECTS_COLLECTION = "projects"
METADATA_COLLECTION = "metadata"
SERVER_SELECTION_TIMEOUT_MS = 2000


def _get_mongo_client():
    """Create a MongoDB client only when pymongo is installed."""
    from pymongo import MongoClient

    return MongoClient(
        MONGODB_URI,
        serverSelectionTimeoutMS=SERVER_SELECTION_TIMEOUT_MS,
    )


def initialize_database(seed_path: Path) -> dict[str, Any]:
    """Connect to MongoDB, create project_data, and seed projects if needed."""
    try:
        client = _get_mongo_client()
        database = client[MONGODB_DB_NAME]
        database.command("ping")

        database[METADATA_COLLECTION].update_one(
            {"name": "projectpilot"},
            {
                "$set": {
                    "name": "projectpilot",
                    "database": MONGODB_DB_NAME,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )

        projects_collection = database[PROJECTS_COLLECTION]
        if projects_collection.count_documents({}) == 0:
            projects = load_projects(seed_path)
            records = projects.to_dict("records")
            if records:
                projects_collection.insert_many(records)
                projects_collection.create_index("project_id", unique=True)

        return {
            "connected": True,
            "database": MONGODB_DB_NAME,
            "projects": projects_collection.count_documents({}),
        }
    except Exception as exc:
        return {
            "connected": False,
            "database": MONGODB_DB_NAME,
            "error": str(exc),
        }
    finally:
        if "client" in locals():
            client.close()


def load_projects_from_mongodb() -> pd.DataFrame:
    """Load project records from MongoDB."""
    client = _get_mongo_client()
    try:
        database = client[MONGODB_DB_NAME]
        database.command("ping")
        records = list(database[PROJECTS_COLLECTION].find({}, {"_id": 0}))
    finally:
        client.close()

    if not records:
        return pd.DataFrame()

    return normalize_project_dataframe(pd.DataFrame(records)).fillna("")


def get_database_status(seed_path: Path) -> dict[str, Any]:
    """Return MongoDB connection and database status."""
    return initialize_database(seed_path)
