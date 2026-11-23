"""FastAPI backend for ProjectPilot AI."""

import logging
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas import (
    FilterOptions,
    HealthResponse,
    ProjectDetail,
    ProjectSummary,
    RecommendationRequest,
    RecommendationResponse,
)
from backend.database import (
    get_database_status,
    initialize_database,
    load_projects_from_mongodb,
)
from backend.store import ProjectStore
from src.data_loader import load_projects
from src.recommender import RecommendationEngine, UserQuery
from src.serializers import (
    build_filter_options,
    project_detail_dict,
    project_summary_dict,
    timeline_for,
)
from src.timeline import (
    resolve_deadline,
    resolve_start_date,
    time_budget_days,
)


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "projects.json"

app = FastAPI(
    title="ProjectPilot AI Backend",
    description="Backend API for intelligent student project recommendations.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB is the preferred project store. The JSON fallback keeps local
# development usable before pymongo or a MongoDB server is configured. The store
# caches the prepared engine so requests do not reload data or refit TF-IDF.
project_store = ProjectStore(
    mongo_loader=lambda: load_projects_from_mongodb(),
    json_loader=lambda: load_projects(DATA_PATH),
)


@app.on_event("startup")
def startup() -> None:
    """Initialize MongoDB when it is available."""
    initialize_database(DATA_PATH)


def get_engine() -> RecommendationEngine:
    """Return the cached recommendation engine (MongoDB first, JSON fallback)."""
    return project_store.get_engine()


def get_projects() -> pd.DataFrame:
    """Return the cleaned, de-duplicated project table."""
    return get_engine().projects


def normalize_any(value: str) -> str:
    """Treat empty strings and 'Any' as no filter."""
    cleaned_value = (value or "").strip()
    return "" if cleaned_value.lower() == "any" else cleaned_value


def project_to_detail(project: pd.Series, start=None, deadline=None) -> ProjectDetail:
    """Convert one project row into a detailed API response."""
    start = start or resolve_start_date()
    return ProjectDetail(**project_detail_dict(project, timeline_for(project, start, deadline)))


def project_to_summary(project: pd.Series, start=None, deadline=None) -> ProjectSummary:
    """Convert one recommended project row into a compact API response."""
    start = start or resolve_start_date()
    return ProjectSummary(**project_summary_dict(project, timeline_for(project, start, deadline)))


@app.get("/", response_model=dict[str, str])
def root() -> dict[str, str]:
    """Default route with a short API message."""
    return {
        "message": "ProjectPilot AI backend is running.",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Check whether the backend can load project data."""
    projects = get_projects()

    return HealthResponse(
        status="ok",
        app_name="ProjectPilot AI Backend",
        total_projects=len(projects),
    )


@app.get("/database", response_model=dict)
def database_status() -> dict:
    """Check MongoDB connection and project_data database status."""
    return get_database_status(DATA_PATH)


@app.get("/options", response_model=FilterOptions)
def get_filter_options() -> FilterOptions:
    """Return filter values for frontend dropdowns."""
    return FilterOptions(**build_filter_options(get_projects()))


@app.get("/projects", response_model=list[ProjectDetail])
def list_projects() -> list[ProjectDetail]:
    """Return all projects with full details."""
    projects = get_projects()
    start = resolve_start_date()

    return [project_to_detail(project, start) for _, project in projects.iterrows()]


@app.get("/projects/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str) -> ProjectDetail:
    """Return full details for one selected project."""
    projects = get_projects()
    matched_projects = projects[projects["project_id"].str.lower() == project_id.strip().lower()]

    if matched_projects.empty:
        raise HTTPException(status_code=404, detail="Project not found")

    return project_to_detail(matched_projects.iloc[0])


@app.post("/recommend", response_model=RecommendationResponse)
def recommend(request: RecommendationRequest) -> RecommendationResponse:
    """Recommend projects from user preferences.

    Results always belong to the requested domain (or any domain for "Any"), are
    ranked by TF-IDF cosine similarity and never repeat a project title.
    """
    try:
        start = resolve_start_date(request.start_date)
        deadline = resolve_deadline(request.deadline, start)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    available_time = normalize_any(request.available_time)
    query = UserQuery(
        domain=normalize_any(request.domain),
        skill_level=normalize_any(request.skill_level),
        interests=(request.interests or "").strip(),
        skills=(request.skills or "").strip(),
        available_time=available_time,
        preferred_language=normalize_any(request.preferred_language),
        time_budget_days=time_budget_days(available_time, start, deadline),
    )

    try:
        engine = get_engine()
        result = engine.recommend(query, top_n=request.top_n)
        recommendations = [
            project_to_summary(project, start, deadline)
            for _, project in result.recommendations.iterrows()
        ]
    except Exception as error:
        logger.exception("Recommendation request failed")
        raise HTTPException(
            status_code=500,
            detail="Could not generate recommendations. Please try again.",
        ) from error

    return RecommendationResponse(
        user_profile=result.profile_text,
        total_projects=len(engine.projects),
        recommendations=recommendations,
        resolved_domain=result.resolution.name,
    )
