"""Shared fixtures for the backend tests (stdlib unittest; pytest also works)."""

from __future__ import annotations

import functools
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_loader import load_projects  # noqa: E402

DATA_PATH = ROOT / "data" / "projects.json"


@functools.lru_cache(maxsize=1)
def _real_projects() -> pd.DataFrame:
    return load_projects(DATA_PATH)


def real_projects() -> pd.DataFrame:
    """The shipped 3,300 project dataset (loaded once, copied per call)."""
    return _real_projects().copy()


@functools.lru_cache(maxsize=1)
def real_engine():
    from src.recommender import RecommendationEngine

    return RecommendationEngine(_real_projects())


_DEFAULTS = {
    "title": "Untitled",
    "domain": "Machine Learning",
    "skill_level": "Beginner",
    "interests": "",
    "available_time": "4-7 Days",
    "preferred_language": "Python",
    "description": "",
    "learning_roadmap": "Plan|Build",
    "required_skills": "",
    "required_libraries": "",
    "free_datasets": "",
    "free_apis": "",
    "learning_resources": "Docs",
    "future_scope": "Scale",
}


def make_projects(*rows: dict) -> pd.DataFrame:
    """Build a small project frame; unspecified columns get neutral defaults."""
    records = []
    for index, row in enumerate(rows, start=1):
        record = dict(_DEFAULTS)
        record["project_id"] = f"T-{index:03d}"
        record.update(row)
        records.append(record)
    return pd.DataFrame(records)
