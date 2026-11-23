"""Quick backend readiness check for ProjectPilot AI."""

from backend.app import get_filter_options, health_check, recommend
from backend.schemas import RecommendationRequest


def main() -> None:
    """Run a small recommendation check without starting the web server."""
    health = health_check()
    options = get_filter_options()
    request = RecommendationRequest(
        domain="Machine Learning",
        skill_level="Beginner",
        interests="recommendation dashboard",
        available_time="2-3 weeks",
        preferred_language="Python",
        top_n=3,
    )
    response = recommend(request)

    print("Backend import: OK")
    print(f"Dataset projects: {health.total_projects}")
    print(f"Available domains: {', '.join(options.domains)}")
    print("Sample recommendations:")

    for index, project in enumerate(response.recommendations, start=1):
        print(f"{index}. {project.title} ({project.match_percentage}%)")


if __name__ == "__main__":
    main()
