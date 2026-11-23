"""ProjectPilot AI - Intelligent Project Recommendation & Learning Assistant."""

from pathlib import Path

import streamlit as st

from src.data_loader import load_projects
from src.project_details import split_items
from src.recommender import build_user_profile, recommend_projects
from src.theme import apply_theme, show_hero


DATA_PATH = Path("data/projects.json")


st.set_page_config(
    page_title="ProjectPilot AI",
    page_icon="PP",
    layout="wide",
)

apply_theme()


@st.cache_data
def get_projects():
    """Load project data once and reuse it during the Streamlit session."""
    return load_projects(DATA_PATH)


def show_list(title: str, value: str) -> None:
    """Display a pipe-separated field as a small bullet list."""
    items = split_items(value)

    if not items:
        st.write(f"**{title}:** Not required")
        return

    st.write(f"**{title}:**")
    for item in items:
        st.write(f"- {item}")


def show_project_details(project) -> None:
    """Show the complete learning assistant details for one project."""
    st.subheader(project["title"])
    st.caption(
        f"{project['domain']} | {project['skill_level']} | "
        f"{project['available_time']} | {project['preferred_language']}"
    )

    st.write(project["description"])

    left, right = st.columns(2)
    with left:
        show_list("Learning roadmap", project["learning_roadmap"])
        show_list("Required skills", project["required_skills"])
        show_list("Required libraries", project["required_libraries"])

    with right:
        show_list("Free datasets", project["free_datasets"])
        show_list("Free APIs", project["free_apis"])
        show_list("Learning resources", project["learning_resources"])

    show_list("Future scope", project["future_scope"])


def main() -> None:
    """Run the Streamlit app."""
    projects = get_projects()

    show_hero()

    with st.sidebar:
        st.header("Your Preferences")

        domain = st.selectbox(
            "Domain",
            ["Any"] + sorted(projects["domain"].unique().tolist()),
        )
        skill_level = st.selectbox(
            "Skill Level",
            ["Any", "Beginner", "Intermediate", "Advanced"],
        )
        available_time = st.selectbox(
            "Available Time",
            ["Any", "1-2 weeks", "2-3 weeks", "3-4 weeks", "4-5 weeks", "5-6 weeks"],
        )
        preferred_language = st.selectbox(
            "Preferred Programming Language",
            ["Any"] + sorted(projects["preferred_language"].unique().tolist()),
        )
        interests = st.text_input(
            "Interests",
            placeholder="Example: NLP, finance, dashboard, healthcare",
        )
        top_n = st.slider("Number of recommendations", min_value=3, max_value=10, value=5)

        submitted = st.button("Recommend Projects", type="primary", use_container_width=True)

    if not submitted:
        st.info("Enter your preferences in the sidebar and click Recommend Projects.")
        st.dataframe(
            projects[["title", "domain", "skill_level", "available_time", "preferred_language"]],
            use_container_width=True,
            hide_index=True,
        )
        return

    user_profile = build_user_profile(
        domain="" if domain == "Any" else domain,
        skill_level="" if skill_level == "Any" else skill_level,
        interests=interests,
        available_time="" if available_time == "Any" else available_time,
        preferred_language="" if preferred_language == "Any" else preferred_language,
    )

    recommendations = recommend_projects(projects, user_profile, top_n=top_n)

    st.header("Top Matching Projects")

    for index, project in recommendations.iterrows():
        match_percentage = round(project["match_score"] * 100, 1)

        with st.container(border=True):
            st.subheader(f"{index + 1}. {project['title']}")
            st.caption(
                f"Match score: {match_percentage}% | {project['domain']} | "
                f"{project['skill_level']} | {project['available_time']}"
            )
            st.write(project["description"])

            with st.expander("View full project plan"):
                show_project_details(project)


if __name__ == "__main__":
    main()
