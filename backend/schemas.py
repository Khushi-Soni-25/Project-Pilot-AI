"""Request and response models for the ProjectPilot AI backend."""

from typing import Optional

from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    """User preferences sent by the frontend."""

    domain: Optional[str] = Field(default="", examples=["Machine Learning"])
    skill_level: Optional[str] = Field(default="", examples=["Beginner"])
    interests: Optional[str] = Field(default="", examples=["recommendation dashboard NLP"])
    available_time: Optional[str] = Field(default="", examples=["8-15 Days"])
    preferred_language: Optional[str] = Field(default="", examples=["Python"])
    top_n: int = Field(default=5, ge=1, le=10)

    # Optional extras. Omitting them gives exactly the previous behaviour.
    skills: Optional[str] = Field(default="", examples=["python, pandas, sql"])
    start_date: Optional[str] = Field(
        default=None,
        description="ISO-8601 date the project would start. Defaults to today (UTC).",
        examples=["2026-03-01"],
    )
    deadline: Optional[str] = Field(
        default=None,
        description="Actual ISO-8601 deadline, if there is one. Never derived from durations.",
        examples=["2026-03-20"],
    )


class DurationEstimate(BaseModel):
    """Estimated effort taken from the project dataset."""

    label: str
    min_days: int
    max_days: int


class CompletionWindow(BaseModel):
    """Estimated finish dates: start date + estimated duration."""

    earliest: str
    latest: str


class TimelineInfo(BaseModel):
    """Timeline for one project. Estimates and the actual deadline are separate."""

    timezone: str = "UTC"
    start_date: str
    estimated_duration: Optional[DurationEstimate] = None
    estimated_completion: Optional[CompletionWindow] = None
    deadline: Optional[str] = None
    days_until_deadline: Optional[int] = None
    fits_deadline: Optional[bool] = None


class ProjectSummary(BaseModel):
    """Small project card returned in recommendation results."""

    project_id: str
    title: str
    domain: str
    skill_level: str
    available_time: str
    preferred_language: str
    description: str
    match_score: float
    match_percentage: float
    timeline: Optional[TimelineInfo] = None


class ProjectDetail(BaseModel):
    """Complete project information shown after a project is selected."""

    project_id: str
    title: str
    domain: str
    skill_level: str
    interests: list[str]
    available_time: str
    preferred_language: str
    description: str
    learning_roadmap: list[str]
    required_skills: list[str]
    required_libraries: list[str]
    free_datasets: list[str]
    free_apis: list[str]
    learning_resources: list[str]
    future_scope: list[str]
    timeline: Optional[TimelineInfo] = None


class RecommendationResponse(BaseModel):
    """Response returned by the recommendation endpoint."""

    user_profile: str
    total_projects: int
    recommendations: list[ProjectSummary]
    # Canonical domain the results were restricted to; null for "Any" or an
    # unrecognised domain (which returns no recommendations).
    resolved_domain: Optional[str] = None


class FilterOptions(BaseModel):
    """Dropdown options used by the frontend."""

    domains: list[str]
    skill_levels: list[str]
    available_times: list[str]
    preferred_languages: list[str]


class HealthResponse(BaseModel):
    """Simple health-check response."""

    status: str
    app_name: str
    total_projects: int
