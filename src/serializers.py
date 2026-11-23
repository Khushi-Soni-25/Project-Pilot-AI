"""Pure helpers that shape project data for the API.

Kept free of FastAPI/pydantic so they can be unit-tested directly. The pydantic
models in ``backend.schemas`` are built from the plain dicts returned here, which
keeps field names and types in one place.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

import pandas as pd

from src.domains import DomainResolver
from src.project_details import split_items
from src.recommender import LEVEL_ORDER, normalize_level
from src.timeline import build_timeline, duration_sort_key


def _get(row: Mapping, column: str) -> str:
    """Cell as clean text; missing columns and NaN/None become ""."""
    value = row.get(column, "") if hasattr(row, "get") else ""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def split_interests(value: Any) -> list[str]:
    """Split a project's ``interests`` field into clean, de-duplicated items.

    The dataset stores them pipe-separated and several are multi-word
    ("AI Agents"). The old API replaced every space with a pipe, which cut
    "AI Agents" into "AI" and "Agents". Space splitting is now only a fallback for
    the legacy CSV format ("education prediction analytics"), which has no pipes.
    """
    text = _get({"v": value}, "v")
    if "|" in text:
        items = split_items(text)
    elif "," in text or ";" in text:
        items = [part.strip() for part in text.replace(";", ",").split(",") if part.strip()]
    else:
        items = text.split()

    seen: set[str] = set()
    unique = []
    for item in items:
        key = item.casefold()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def project_summary_dict(row: Mapping, timeline: Optional[dict] = None) -> dict:
    """Compact card returned in recommendation results."""
    score = min(max(float(row.get("match_score", 0.0) or 0.0), 0.0), 1.0)
    return {
        "project_id": _get(row, "project_id"),
        "title": _get(row, "title"),
        "domain": _get(row, "domain"),
        "skill_level": _get(row, "skill_level"),
        "available_time": _get(row, "available_time"),
        "preferred_language": _get(row, "preferred_language"),
        "description": _get(row, "description"),
        "match_score": round(score, 4),
        "match_percentage": round(score * 100, 2),
        "timeline": timeline,
    }


def project_detail_dict(row: Mapping, timeline: Optional[dict] = None) -> dict:
    """Complete project information shown after a project is selected."""
    return {
        "project_id": _get(row, "project_id"),
        "title": _get(row, "title"),
        "domain": _get(row, "domain"),
        "skill_level": _get(row, "skill_level"),
        "interests": split_interests(_get(row, "interests")),
        "available_time": _get(row, "available_time"),
        "preferred_language": _get(row, "preferred_language"),
        "description": _get(row, "description"),
        "learning_roadmap": split_items(_get(row, "learning_roadmap")),
        "required_skills": split_items(_get(row, "required_skills")),
        "required_libraries": split_items(_get(row, "required_libraries")),
        "free_datasets": split_items(_get(row, "free_datasets")),
        "free_apis": split_items(_get(row, "free_apis")),
        "learning_resources": split_items(_get(row, "learning_resources")),
        "future_scope": split_items(_get(row, "future_scope")),
        "timeline": timeline,
    }


def timeline_for(row: Mapping, start, deadline=None) -> dict:
    """Timeline block for one project row (see ``src.timeline.build_timeline``)."""
    return build_timeline(_get(row, "available_time"), start, deadline)


def _level_sort_key(level: str) -> tuple:
    canonical = normalize_level(level)
    order = [item.lower() for item in LEVEL_ORDER]
    if canonical in order:
        return (0, order.index(canonical), level)
    return (1, 0, level)


def build_filter_options(projects: pd.DataFrame) -> dict:
    """Dropdown values for the frontend.

    * domains: one entry per real domain (spelling variants collapse), A-Z
    * skill_levels: Beginner -> Intermediate -> Advanced (was alphabetical)
    * available_times: shortest -> longest (was text order, which put
      "1-3 Months" before "4-7 Days")
    * blanks never appear as options
    """

    def clean_values(column: str) -> list[str]:
        if column not in projects.columns:
            return []
        values = (_get({"v": v}, "v") for v in projects[column])
        return sorted({v for v in values if v})

    domains = DomainResolver(projects["domain"] if "domain" in projects.columns else []).domains
    levels = sorted(clean_values("skill_level"), key=_level_sort_key)
    times = sorted(clean_values("available_time"), key=duration_sort_key)

    return {
        "domains": domains,
        "skill_levels": levels,
        "available_times": times,
        "preferred_languages": clean_values("preferred_language"),
    }
