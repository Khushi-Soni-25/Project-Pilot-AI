"""Recommendation engine for ProjectPilot AI.

Pipeline (per request)
----------------------
1. **Resolve the domain** (``src.domains``) to one canonical dataset domain.
2. **Strict domain filter**: only projects of that domain stay eligible. This
   happens *before* any similarity is computed, so another domain can never be
   returned, however well its text matches the interests.
3. **TF-IDF + cosine similarity** over the eligible projects only. A project
   document is built from its title, domain, level, interests/tags, description,
   required skills, libraries, languages and "fits within N days" tokens. The
   user query is built from experience level, interests, skills, language and
   ONE token for the time budget they have (a bounded signal, so availability
   can never outweigh what the user is interested in). The domain itself is
   enforced by step 2; it joins the query only when nothing else was given.
   If a chosen domain matches none of the user's other words, the domain's own
   projects are ranked by domain similarity instead of returning nothing.
4. **Rank** by cosine similarity (ties broken by ``project_id``, so the order is
   deterministic), drop zero-similarity rows, collapse title variants and return
   the top ``n``.

Backward compatibility
----------------------
``build_user_profile`` and ``recommend_projects`` keep their old signatures and
return types (a ``str`` profile and a ``DataFrame`` with ``match_score``), so the
FastAPI layer and the Streamlit app keep working. ``build_user_profile`` returns
a ``str`` subclass that also carries the structured query, which is how
``recommend_projects`` can apply the strict domain filter without its signature
changing.
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from typing import Any, Iterable, Optional

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.data_loader import REQUIRED_COLUMNS, clean_projects
from src.domains import DomainResolution, DomainResolver, domain_key, is_any
from src.timeline import Duration, parse_duration

logger = logging.getLogger(__name__)

PROFILE_COLUMNS = [
    "title",
    "domain",
    "skill_level",
    "interests",
    "available_time",
    "preferred_language",
    "description",
    "required_skills",
    "required_libraries",
]

ESSENTIAL_COLUMNS = ("project_id", "title", "domain")

# Similarities at or below this are "no overlap at all" and never recommended.
MIN_SCORE = 1e-9
SCORE_DECIMALS = 10  # rounds away float jitter so tie-breaking stays deterministic

LEVEL_ORDER = ("Beginner", "Intermediate", "Advanced")
_LEVEL_ALIASES = {
    "beginner": "beginner",
    "novice": "beginner",
    "entry": "beginner",
    "entry level": "beginner",
    "junior": "beginner",
    "fresher": "beginner",
    "student": "beginner",
    "intermediate": "intermediate",
    "mid": "intermediate",
    "mid level": "intermediate",
    "medium": "intermediate",
    "advanced": "advanced",
    "expert": "advanced",
    "senior": "advanced",
}

# sklearn's list removes words that are real vocabulary here: "system(s)" as in
# "Expert Systems", "full" as in "Full Stack", and front/back as in front end.
STOP_WORDS = frozenset(ENGLISH_STOP_WORDS) - {"system", "full", "front", "back", "interest"}

# --------------------------------------------------------------------------- #
# Text normalization
# --------------------------------------------------------------------------- #

_TOKEN_RE = re.compile(r"(?u)\b\w\w+\b")
_ITEM_SPLIT_RE = re.compile(r"[,;|/\n]+")

# Symbols the default tokenizer would erase ("C++" -> nothing).
_SYMBOL_PATTERNS = (
    (re.compile(r"(?<![a-z0-9])c\+\+"), " cpp "),
    (re.compile(r"(?<![a-z0-9])c#"), " csharp "),
    (re.compile(r"(?<![a-z0-9])f#"), " fsharp "),
    (re.compile(r"(?<![a-z0-9])\.net\b"), " dotnet "),
    (re.compile(r"\bnode\.js\b"), " nodejs "),
    (re.compile(r"\breact\.js\b"), " reactjs "),
    (re.compile(r"\bvue\.js\b"), " vuejs "),
    (re.compile(r"\bnext\.js\b"), " nextjs "),
)

# Languages that are one letter or a stop word ("R", "C", "Go") would vanish.
# Applied only to whole list items / whole words of language & skill fields.
_ITEM_ALIASES = {"r": "rlang", "c": "clang", "go": "golang", "c++": "cpp", "c#": "csharp"}


def _text(value: Any) -> str:
    """Safe string for any cell: None/NaN/NA -> "", everything else stripped text."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass  # list-likes: fall through to str()
    return str(value).strip()


def normalize_text(text: Any) -> str:
    """Lower-case and protect symbol-heavy tech names before tokenization."""
    cleaned = _text(text).casefold()
    for pattern, replacement in _SYMBOL_PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned


def split_items(value: Any) -> list[str]:
    """Split a list-like text field (``a|b``, ``a, b``, ``a; b``) into items."""
    return [item.strip() for item in _ITEM_SPLIT_RE.split(_text(value)) if item.strip()]


def normalize_items(value: Any, *, word_level: bool = False) -> list[str]:
    """Items of a list-like field with one-letter/stop-word languages protected.

    ``word_level`` also rewrites such words inside an item (``"python r sql"``);
    use it for skills/languages, not for free-text interests.
    """
    items = []
    for item in split_items(value):
        lowered = item.casefold()
        if lowered in _ITEM_ALIASES:
            items.append(_ITEM_ALIASES[lowered])
        elif word_level:
            items.append(" ".join(_ITEM_ALIASES.get(word, word) for word in lowered.split()))
        else:
            items.append(item)
    return items


def _fold_plural(token: str) -> str:
    """Conservative plural folding so "dashboards" matches "dashboard"."""
    if len(token) < 4 or not token.isalpha():
        return token
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith(("ss", "us", "is")):
        return token
    if token.endswith("s"):
        return token[:-1]
    return token


def analyze_text(text: str) -> list[str]:
    """Analyzer handed to ``TfidfVectorizer``: unigrams plus within-line bigrams.

    Lines (``\\n``) are field/item boundaries, so bigrams never span two
    different fields ("tracker machine" can not appear). Stop words are removed
    before plural folding and bigrams are built from the remaining tokens.
    """
    tokens: list[str] = []
    bigrams: list[str] = []
    for line in normalize_text(text).split("\n"):
        line_tokens = [
            _fold_plural(token)
            for token in _TOKEN_RE.findall(line)
            if token not in STOP_WORDS
        ]
        tokens.extend(line_tokens)
        bigrams.extend(f"{a} {b}" for a, b in zip(line_tokens, line_tokens[1:]))
    return tokens + bigrams


def _fit_token(days: int) -> str:
    """Token meaning "can be finished within ``days`` days"."""
    return f"fits_{days}d"


def normalize_level(value: Any) -> str:
    """Canonical lower-case level ("Senior" -> "advanced"); "" for Any/empty."""
    key = domain_key(value)
    if is_any(key):
        return ""
    return _LEVEL_ALIASES.get(key, key)


# --------------------------------------------------------------------------- #
# Query objects
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class UserQuery:
    """What the user told us. Every field is optional and may be "Any"/empty."""

    domain: str = ""
    skill_level: str = ""  # experience
    interests: str = ""
    skills: str = ""
    available_time: str = ""
    preferred_language: str = ""
    # Days the user can spend. When None it is derived from ``available_time``.
    time_budget_days: Optional[int] = None


class UserProfile(str):
    """Readable profile text that also carries the structured ``UserQuery``."""

    query: UserQuery

    def __new__(cls, text: str, query: UserQuery) -> "UserProfile":
        obj = super().__new__(cls, text)
        obj.query = query
        return obj


def _profile_text(query: UserQuery, resolution: Optional[DomainResolution] = None) -> str:
    parts = []
    for value in (
        query.domain,
        query.skill_level,
        query.interests,
        query.skills,
        query.available_time,
        query.preferred_language,
    ):
        cleaned = _text(value)
        if cleaned and not is_any(cleaned):
            parts.append(cleaned)
    return " ".join(" ".join(parts).lower().split())


def build_user_profile(
    domain: str,
    skill_level: str,
    interests: str,
    available_time: str,
    preferred_language: str,
    skills: str = "",
) -> UserProfile:
    """Convert user preferences into one searchable text profile.

    Returns a ``str`` (as before) that also exposes ``.query``.
    """
    query = UserQuery(
        domain=_text(domain),
        skill_level=_text(skill_level),
        interests=_text(interests),
        skills=_text(skills),
        available_time=_text(available_time),
        preferred_language=_text(preferred_language),
    )
    return UserProfile(_profile_text(query), query)


# --------------------------------------------------------------------------- #
# Engine
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RecommendationResult:
    """Ranked recommendations plus the context needed to explain them."""

    recommendations: pd.DataFrame
    resolution: DomainResolution
    profile_text: str
    eligible_count: int


class _Index:
    """TF-IDF matrix for one eligible subset of projects."""

    def __init__(self, documents: list[str], positions: np.ndarray):
        self.positions = positions
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.matrix = None
        try:
            vectorizer = TfidfVectorizer(
                analyzer=analyze_text,
                sublinear_tf=True,
                norm="l2",
            )
            self.matrix = vectorizer.fit_transform(documents)
            self.vectorizer = vectorizer
        except ValueError:
            # "empty vocabulary": every document was blank. Nothing can match.
            logger.warning("TF-IDF index has an empty vocabulary (%d documents)", len(documents))

    def score(self, query_text: str) -> np.ndarray:
        if self.vectorizer is None or not query_text.strip():
            return np.zeros(len(self.positions))
        query_vector = self.vectorizer.transform([query_text])
        if query_vector.nnz == 0:
            return np.zeros(len(self.positions))
        return cosine_similarity(query_vector, self.matrix).ravel()


class RecommendationEngine:
    """Strict-domain TF-IDF/cosine recommender over a project DataFrame.

    Build one engine per dataset and reuse it: documents are prepared once and a
    TF-IDF index is fitted lazily per domain (and once for "Any") and cached.
    Instances are safe to share between threads.
    """

    def __init__(self, projects: pd.DataFrame):
        # None / a frame without columns is a valid, empty dataset.
        frame = clean_projects(projects if projects is not None else pd.DataFrame())

        missing = [c for c in ESSENTIAL_COLUMNS if c not in frame.columns]
        if missing:
            raise ValueError(f"Projects are missing required columns: {', '.join(missing)}")
        for column in REQUIRED_COLUMNS:
            if column not in frame.columns:
                frame[column] = ""

        self.projects: pd.DataFrame = frame
        self.resolver = DomainResolver(frame["domain"])

        self._domain_keys = np.array([domain_key(v) for v in frame["domain"]], dtype=object)
        self._dedupe_keys = np.array(
            [
                f"{_text(t).casefold()}|{dk}|{normalize_level(level)}"
                for t, dk, level in zip(frame["title"], self._domain_keys, frame["skill_level"])
            ],
            dtype=object,
        )

        durations = [parse_duration(v) for v in frame["available_time"]]
        # Distinct "latest finish" values in the data (3, 7, 15, 30, 90 days ...).
        self._budget_levels: list[int] = sorted({d.max_days for d in durations if d is not None})
        self._documents = [
            self._document(row, duration)
            for row, duration in zip(frame.to_dict("records"), durations)
        ]

        self._indexes: dict[Optional[str], _Index] = {}
        self._lock = threading.Lock()

    # -- documents & queries ------------------------------------------------ #

    def _document(self, row: dict, duration: Optional[Duration]) -> str:
        """One project -> one text document (one field/item per line)."""
        lines = [
            _text(row.get("title")),
            _text(row.get("domain")),
            normalize_level(row.get("skill_level")),
            *split_items(row.get("interests")),
            _text(row.get("description")),
            *normalize_items(row.get("required_skills"), word_level=True),
            *normalize_items(row.get("required_libraries"), word_level=True),
            *normalize_items(row.get("preferred_language"), word_level=True),
        ]
        if duration is not None:
            # "Fits within L days" for every budget level L the project finishes in.
            lines.extend(
                _fit_token(level) for level in self._budget_levels if level >= duration.max_days
            )
        return "\n".join(line for line in lines if line)

    def _time_budget_token(self, budget_days: Optional[int]) -> list[str]:
        """The single "fits within N days" token for the user's budget (or none)."""
        if budget_days is None:
            return []
        levels = [level for level in self._budget_levels if level <= budget_days]
        return [_fit_token(max(levels))] if levels else []

    def build_query_text(self, query: UserQuery, resolution: DomainResolution) -> str:
        """Query document: one field/item per line, mirroring ``_document``."""
        budget = query.time_budget_days
        if budget is None:
            parsed = parse_duration(query.available_time)
            budget = parsed.max_days if parsed else None

        lines = [
            normalize_level(query.skill_level),
            *split_items(query.interests),
            *normalize_items(query.skills, word_level=True),
            *(
                []
                if is_any(query.preferred_language)
                else normalize_items(query.preferred_language, word_level=True)
            ),
            *self._time_budget_token(budget),
        ]
        lines = [line for line in lines if line]
        # The strict filter already guarantees the domain, and every eligible
        # project shares it, so the domain name carries no ranking information and
        # would only favour sparse documents. It is used only when it is the one
        # thing the user gave us, so a domain-only request still gets results.
        if not lines and resolution.name:
            lines = [resolution.name]
        return "\n".join(lines)

    # -- indexes ------------------------------------------------------------ #

    def _eligible_positions(self, resolution: DomainResolution) -> np.ndarray:
        """Row positions allowed by the strict domain filter."""
        if resolution.status == "matched":
            return np.flatnonzero(self._domain_keys == resolution.key)
        return np.arange(len(self.projects))

    def _index_for(self, resolution: DomainResolution, positions: np.ndarray) -> _Index:
        cache_key = resolution.key if resolution.status == "matched" else None
        index = self._indexes.get(cache_key)
        if index is None:
            with self._lock:
                index = self._indexes.get(cache_key)
                if index is None:
                    index = _Index([self._documents[i] for i in positions], positions)
                    self._indexes[cache_key] = index
        return index

    # -- public API --------------------------------------------------------- #

    def _empty(self) -> pd.DataFrame:
        frame = self.projects.iloc[0:0].copy()
        frame["match_score"] = pd.Series(dtype="float64")
        return frame

    def recommend(
        self,
        query: UserQuery,
        top_n: int = 5,
        *,
        dedupe: bool = True,
    ) -> RecommendationResult:
        """Rank projects for ``query``. See the module docstring for the pipeline."""
        try:
            top_n = max(int(top_n), 0)
        except (TypeError, ValueError):
            top_n = 5

        resolution = self.resolver.resolve(query.domain)
        profile_text = _profile_text(query)

        # Unknown domain: never fall back to other domains.
        if top_n == 0 or self.projects.empty or resolution.status == "unknown":
            return RecommendationResult(self._empty(), resolution, profile_text, 0)

        positions = self._eligible_positions(resolution)  # strict filter FIRST
        if positions.size == 0:
            return RecommendationResult(self._empty(), resolution, profile_text, 0)

        index = self._index_for(resolution, positions)
        ranked = self._rank(index, self.build_query_text(query, resolution), dedupe)

        if ranked.empty and resolution.status == "matched":
            # The user chose a domain but none of their other words occur in it.
            # Showing that domain's projects (with low, honest scores) beats an
            # empty page. "Any" has no domain to fall back to, so it stays empty.
            ranked = self._rank(index, resolution.name or "", dedupe)

        result = ranked.head(top_n).reset_index(drop=True)
        return RecommendationResult(result, resolution, profile_text, int(positions.size))

    def _rank(self, index: _Index, query_text: str, dedupe: bool) -> pd.DataFrame:
        """Score the index against ``query_text`` and return ranked candidates."""
        scores = np.round(index.score(query_text), SCORE_DECIMALS)

        candidates = self.projects.iloc[index.positions].copy()
        candidates["match_score"] = scores
        candidates["_dedupe_key"] = self._dedupe_keys[index.positions]
        candidates = candidates[candidates["match_score"] > MIN_SCORE]

        candidates = candidates.sort_values(
            ["match_score", "project_id"], ascending=[False, True], kind="mergesort"
        )
        if dedupe:
            candidates = candidates.drop_duplicates(subset="_dedupe_key", keep="first")
        return candidates.drop(columns="_dedupe_key")


def build_project_profiles(projects: pd.DataFrame) -> pd.Series:
    """Combine important project columns into one text profile per project."""
    engine = RecommendationEngine(projects)
    return pd.Series(engine._documents, index=engine.projects.index, dtype="object")


def recommend_projects(
    projects: pd.DataFrame,
    user_profile: Any,
    top_n: int = 5,
    *,
    engine: Optional[RecommendationEngine] = None,
) -> pd.DataFrame:
    """Return the top matching projects for a user profile (legacy entry point).

    ``user_profile`` should come from ``build_user_profile`` so the strict domain
    filter can be applied. A plain string is treated as free-text interests and
    carries no domain information, so it cannot be domain-filtered.

    Pass a prebuilt ``engine`` to reuse cached TF-IDF indexes between calls.
    """
    engine = engine or RecommendationEngine(projects)
    query = getattr(user_profile, "query", None)
    if not isinstance(query, UserQuery):
        query = UserQuery(interests=_text(user_profile))
    return engine.recommend(query, top_n=top_n).recommendations
