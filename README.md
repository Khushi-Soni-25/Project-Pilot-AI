# ProjectPilot AI

ProjectPilot AI is an intelligent project recommendation and learning assistant
for students. It recommends project ideas based on a student's domain, skill
level, interests, available time, and preferred programming language.

## What The App Does

1. The user enters project preferences.
2. The recommendation engine compares those preferences with the project dataset.
3. The app shows the top matching projects.
4. Each selected project includes:
   - project description
   - learning roadmap
   - required skills
   - required libraries
   - free datasets
   - free APIs
   - learning resources
   - future scope

## Tech Stack

- Python
- Pandas
- NumPy
- Scikit-learn
- Streamlit
- FastAPI
- Uvicorn
- MongoDB
- JSON project database fallback

## How Recommendation Works

This first version uses a content-based recommendation approach.

- Project details are combined into a text profile.
- User preferences are combined into a text profile.
- `TfidfVectorizer` converts text into numeric vectors.
- `cosine_similarity` scores how closely each project matches the user.

This approach is beginner-friendly, explainable, and suitable for an AI/ML
internship project.

### Domain accuracy, ranking and timelines

- **Strict domain filter.** The selected domain is resolved (`src/domains.py`:
  case/punctuation-insensitive names plus a controlled alias table such as
  `ML`, `NLP`, `IoT`) to one dataset domain, and only that domain's projects are
  scored. An unrecognised domain returns no results; it never falls back to
  other domains. `Any` means no restriction.
- **TF-IDF + cosine.** Scores are `cosine_similarity` between the user's query
  (experience level, interests, optional `skills`, language, time budget) and
  each eligible project's text (title, tags, description, skills, libraries,
  languages). Ties break by `project_id`; zero-similarity rows are dropped;
  projects sharing a title collapse to the best-scoring variant.
- **Timelines.** `estimated_completion_time` is parsed (`4-7 Days`, `1-3 Months`,
  legacy `2-3 weeks`). Each result carries a `timeline` block (UTC, ISO dates):
  `start_date` (request `start_date`, default today), `estimated_completion`
  (start + duration), and the caller's actual `deadline` with `fits_deadline`.
  Estimates and deadlines are never derived from each other.
- **New optional request fields** (existing clients are unaffected): `skills`,
  `start_date`, `deadline`. New optional response fields: `timeline`,
  `resolved_domain`.
- Project data is cached in memory (`PROJECT_CACHE_TTL_SECONDS`, default 60;
  `MONGO_RETRY_SECONDS`, default 60) instead of reloaded on every request.

### Tests

```bash
python -m unittest discover -s tests -t .      # or: pytest
```


## Folder Structure

```text
.
├── main.py
├── backend/
│   ├── __init__.py
│   ├── app.py
│   └── schemas.py
├── frontend/
│   ├── index.html          (landing page)
│   ├── app.html            (project matcher workspace)
│   ├── favicon.svg
│   ├── fonts/              (self-hosted Sora + Geist)
│   ├── css/
│   │   ├── tokens.css      (colours, type, spacing, motion)
│   │   ├── base.css        (nav, buttons, badges, glass, footer)
│   │   ├── landing.css
│   │   └── workspace.css
│   └── js/
│       ├── api.js          (backend client)
│       ├── icons.js        (inline SVG icon sprite)
│       ├── ui.js           (nav, scroll reveal, count-up)
│       ├── landing.js      (live stats from the API)
│       └── app.js          (form, results, details drawer)
├── .streamlit/config.toml  (Streamlit dark theme)
├── data/
│   └── projects.csv
├── src/
│   ├── __init__.py
│   ├── data_loader.py
│   ├── project_details.py
│   └── recommender.py
├── requirements.txt
└── README.md
```

## File Guide

- `main.py`: Streamlit user interface.
- `backend/app.py`: FastAPI backend with API routes.
- `backend/schemas.py`: Request and response validation models.
- `frontend/index.html`: Landing page (hero, features, how it works, dataset metrics).
- `frontend/app.html`: Project matcher workspace (preferences, ranked results, plan drawer).
- `frontend/css/tokens.css`: Design tokens. Change colours and type here.
- `frontend/css/base.css`, `landing.css`, `workspace.css`: Shared and page styles.
- `frontend/js/api.js`: Backend API helper functions.
- `frontend/js/app.js`: Form handling, rendering, and page interactions.
- `src/theme.py`: Dark theme styles for the Streamlit UI.
- `run_frontend.py`: Local static server for the frontend.
- `data/projects.json`: Project database used by the recommender.
- `scripts/generate_projects_json.py`: Regenerates the 3,300-project JSON database.
- `src/data_loader.py`: Loads and validates the project dataset.
- `src/recommender.py`: Builds text profiles and recommends projects.
- `src/project_details.py`: Formats dataset fields for display.

## Run Locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure MongoDB:

```bash
cp .env.example .env
```

Then set `MONGODB_URI` if you are using MongoDB Atlas or a non-default local
server. The default database name is `project_data`.

Start the app:

```bash
streamlit run main.py
```

Then open the local URL shown in the terminal.

## Run The Backend

Start the FastAPI backend:

```bash
python run_backend.py
```

Alternative command:

```bash
uvicorn backend.app:app --reload
```

Open the interactive API docs:

```text
http://127.0.0.1:8000/docs
```

## Backend API Routes

- `GET /`: Check that the API is running.
- `GET /health`: Check dataset loading and total project count.
- `GET /database`: Check MongoDB connection and `project_data` status.
- `GET /options`: Get dropdown options for domain, skill level, time, and language.
- `GET /projects`: Get all project details.
- `GET /projects/{project_id}`: Get one project by ID, for example `/projects/P001`.
- `POST /recommend`: Recommend projects from user preferences.

Example recommendation request:

```json
{
  "domain": "Machine Learning",
  "skill_level": "Beginner",
  "interests": "recommendation dashboard",
  "available_time": "2-3 weeks",
  "preferred_language": "Python",
  "top_n": 5
}
```

## Run The Frontend

Open a second terminal and start the static frontend server:

```bash
python run_frontend.py
```

Then open:

```text
http://127.0.0.1:5500
```

By default the frontend calls the deployed API. To use a local backend, add
`<script>window.PROJECTPILOT_API_BASE = "http://127.0.0.1:8000";</script>`
before `js/api.js` in `index.html` and `app.html`.

For the full app experience, keep both servers running:

```text
Backend:  http://127.0.0.1:8000
Frontend: http://127.0.0.1:5500
```

## Future Improvements

- Add project search and filters.
- Add user feedback and ratings.
- Store projects in JSON or SQLite.
- Add downloadable learning roadmaps.
- Add a simple admin page to add new projects.
- Add evaluation metrics for recommendation quality.
