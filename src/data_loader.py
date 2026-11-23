"""Utilities for loading and validating ProjectPilot AI datasets."""

import json
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "project_id",
    "title",
    "domain",
    "skill_level",
    "interests",
    "available_time",
    "preferred_language",
    "description",
    "learning_roadmap",
    "required_skills",
    "required_libraries",
    "free_datasets",
    "free_apis",
    "learning_resources",
    "future_scope",
}


def load_projects(csv_path: str | Path) -> pd.DataFrame:
    """Load the project dataset and check that all required columns exist."""
    path = Path(csv_path)

    if not path.exists():
        raise FileNotFoundError(f"Project dataset not found: {path}")

    if path.suffix.lower() == ".json":
        projects = _load_json_projects(path)
    else:
        projects = pd.read_csv(path)

    return clean_projects(normalize_project_dataframe(projects).fillna(""))


def normalize_project_dataframe(projects: pd.DataFrame) -> pd.DataFrame:
    """Normalize and validate a project dataframe from any supported source."""
    normalized_projects = _normalize_project_columns(projects)
    missing_columns = REQUIRED_COLUMNS.difference(normalized_projects.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Dataset is missing required columns: {missing}")

    return normalized_projects


def _load_json_projects(path: Path) -> pd.DataFrame:
    """Load ProjectPilot's rich JSON dataset."""
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        records = data.get("projects", [])
    else:
        records = data

    if not isinstance(records, list):
        raise ValueError(f"Project JSON must hold a list of projects: {path}")

    return pd.DataFrame(records)


def _join_items(value) -> str:
    """Convert JSON list fields into the pipe-separated format used by the UI.

    Missing values (None, NaN, pd.NA) become an empty string. They used to become
    the literal text "nan", which leaked into the UI and into TF-IDF.
    """
    if isinstance(value, (list, tuple, set)):
        return "|".join(str(item).strip() for item in value if str(item).strip())
    if value is None or pd.isna(value):
        return ""
    return str(value)


def _clean_pipe_list(value: str) -> str:
    """Drop empty segments from a pipe-separated string ("a||b|" -> "a|b")."""
    return "|".join(part.strip() for part in str(value).split("|") if part.strip())


def _text_column(projects: pd.DataFrame, column: str, default: str = "") -> pd.Series:
    """Return ``projects[column]`` as clean text, or a ``default`` Series if absent."""
    if column not in projects.columns:
        return pd.Series(default, index=projects.index, dtype="object")
    return projects[column].map(_join_items)


def _normalize_project_columns(projects: pd.DataFrame) -> pd.DataFrame:
    """Map the richer JSON schema into the recommender's compact schema."""
    projects = projects.copy()

    column_map = {
        "project_name": "title",
        "difficulty_level": "skill_level",
        "estimated_completion_time": "available_time",
        "programming_languages": "preferred_language",
        "short_description": "description",
    }

    for source, target in column_map.items():
        if target not in projects.columns and source in projects.columns:
            projects[target] = projects[source]

    if "interests" not in projects.columns:
        interest_parts = []
        for column in ["interest_category", "subdomain", "tags"]:
            if column in projects.columns:
                interest_parts.append(projects[column].map(_join_items))

        if interest_parts:
            interests = interest_parts[0]
            for part in interest_parts[1:]:
                interests = interests + "|" + part
            projects["interests"] = interests.map(_clean_pipe_list)

    if "free_datasets" not in projects.columns and "dataset_name" in projects.columns:
        dataset_links = _text_column(projects, "dataset_link", "Not applicable")
        projects["free_datasets"] = (
            _text_column(projects, "dataset_name") + " - " + dataset_links
        )

    if "free_apis" not in projects.columns and "api_name" in projects.columns:
        api_links = _text_column(projects, "api_link", "Not applicable")
        projects["free_apis"] = _text_column(projects, "api_name") + " - " + api_links

    if "learning_resources" not in projects.columns:
        projects["learning_resources"] = (
            "Official documentation|GitHub examples|freeCodeCamp tutorials|Kaggle Learn"
        )

    for column in [
        "learning_roadmap",
        "required_skills",
        "required_libraries",
        "free_datasets",
        "free_apis",
        "learning_resources",
        "future_scope",
        "preferred_language",
    ]:
        if column in projects.columns:
            projects[column] = projects[column].map(_join_items)

    return projects


_MISSING_MARKERS = {"nan", "none", "null", "<na>"}
# A row is a content duplicate only if EVERY column the recommender reads matches.
_DEDUPE_CONTENT_COLUMNS = [
    "title",
    "domain",
    "skill_level",
    "interests",
    "description",
    "available_time",
    "preferred_language",
    "required_skills",
    "required_libraries",
]


def clean_projects(projects: pd.DataFrame) -> pd.DataFrame:
    """Make a project frame safe for the recommender. Idempotent.

    * every cell becomes stripped text; None/NaN and the literal markers
      "nan"/"none"/"null" become ""
    * rows without a ``project_id`` or ``title`` are dropped (they cannot be shown
      or looked up)
    * duplicate ``project_id`` values (case-insensitive) keep the first row
    * rows identical in every recommender-relevant column (title, domain, level,
      interests, description, time, languages, skills, libraries) under a different
      id are dropped too

    Rows that merely share a title (the dataset holds several variants per
    title) are *not* removed here; the recommender collapses those at ranking
    time so the best-matching variant survives.
    """
    if projects is None or len(projects.columns) == 0:
        return pd.DataFrame(columns=sorted(REQUIRED_COLUMNS))

    cleaned = projects.copy()
    for column in cleaned.columns:
        text = cleaned[column].map(_join_items).astype(str).str.strip()
        cleaned[column] = text.mask(text.str.lower().isin(_MISSING_MARKERS), "")

    for required in ("project_id", "title"):
        if required in cleaned.columns:
            cleaned = cleaned[cleaned[required] != ""]

    if "project_id" in cleaned.columns:
        cleaned = cleaned[~cleaned["project_id"].str.lower().duplicated(keep="first")]

    content_columns = [c for c in _DEDUPE_CONTENT_COLUMNS if c in cleaned.columns]
    if content_columns:
        cleaned = cleaned[~cleaned.duplicated(subset=content_columns, keep="first")]

    return cleaned.reset_index(drop=True)
