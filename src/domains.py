"""Domain normalization, aliases and strict domain resolution.

Why this module exists
----------------------
Domains used to be compared as free text inside the TF-IDF profile, so choosing
"Machine Learning" could still return "Natural Language Processing" projects.
The recommender now resolves the user's domain to ONE canonical dataset domain
through a controlled lookup, and filters on it *before* any similarity maths.

Resolution is deliberately strict and never fuzzy:

* ``""``, ``"Any"``, ``"All"`` ...      -> no filter (``status == "any"``)
* exact / punctuation-insensitive name  -> that domain
* controlled alias (``"ML"``, ``"cv"``)  -> that domain
* anything else                         -> ``status == "unknown"``; callers must
  return no results instead of guessing a "close" domain.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Optional

# Values that mean "the user did not restrict this field". Compared AFTER
# ``domain_key`` normalization, so punctuation is already gone ("N/A" -> "n a").
ANY_VALUES = frozenset({"", "any", "all", "none", "n a", "na", "any domain", "all domains"})

# canonical dataset domain -> accepted aliases. Aliases are matched after
# ``domain_key`` normalization, so case, punctuation and spacing do not matter.
# An alias only becomes active if its canonical domain exists in the dataset, and
# an alias may never point at two different domains (enforced in tests).
DOMAIN_ALIASES: dict[str, tuple[str, ...]] = {
    "Artificial Intelligence": ("ai", "artificial intelligence"),
    "Machine Learning": ("ml", "machine learning"),
    "Deep Learning": ("dl", "deep learning"),
    "Data Science": ("ds", "data science"),
    "Natural Language Processing": ("nlp", "natural language", "natural language processing"),
    "Computer Vision": ("cv", "computer vision"),
    "Recommendation Systems": (
        "recsys",
        "recommender",
        "recommenders",
        "recommender system",
        "recommender systems",
        "recommendation system",
        "recommendation engine",
        "recommendation engines",
    ),
    "Web Development": (
        "web",
        "web dev",
        "webdev",
        "web app",
        "web apps",
        "web application",
        "web applications",
    ),
    "Mobile App Development": (
        "mobile",
        "mobile app",
        "mobile apps",
        "mobile development",
        "app development",
        "app dev",
    ),
    "Cybersecurity": (
        "cyber security",
        "cyber",
        "infosec",
        "information security",
        "security",
    ),
    "Cloud Computing": ("cloud",),
    "DevOps": ("dev ops",),
    "Internet of Things (IoT)": ("iot", "internet of things"),
    "Robotics": ("robot", "robots"),
    "Blockchain": ("block chain", "web3"),
    "Game Development": ("game dev", "gamedev", "games", "gaming"),
    "AR/VR": (
        "arvr",
        "ar",
        "vr",
        "xr",
        "augmented reality",
        "virtual reality",
        "augmented and virtual reality",
    ),
    "Big Data": ("bigdata",),
    "Database Systems": (
        "database",
        "databases",
        "db",
        "dbms",
        "database management",
        "database management systems",
    ),
    "Automation": ("rpa",),
    "Embedded Systems": ("embedded", "embedded system"),
    "UI/UX Design": (
        "ui",
        "ux",
        "ux ui",
        "ui design",
        "ux design",
        "user interface",
        "user experience",
        "user interface design",
    ),
}


def _is_missing(value) -> bool:
    """True for None, NaN and pandas NA without importing pandas."""
    if value is None:
        return True
    try:
        return bool(value != value)  # NaN != NaN; pd.NA raises TypeError below
    except TypeError:
        return True


def domain_key(value) -> str:
    """Canonical comparison key for a domain-like string.

    Lower-cases, folds unicode, turns ``&`` into ``and`` and collapses every run
    of punctuation/whitespace into a single space::

        "Internet of Things (IoT)" -> "internet of things iot"
        "UI/UX  Design"            -> "ui ux design"
    """
    if _is_missing(value):
        return ""
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    text = text.replace("&", " and ")
    text = re.sub(r"[\W_]+", " ", text)
    return text.strip()


def compact_key(value) -> str:
    """``domain_key`` without spaces, so "Cyber Security" == "Cybersecurity"."""
    return domain_key(value).replace(" ", "")


def is_any(value) -> bool:
    """True when the value means "no restriction" (empty, Any, All ...)."""
    return domain_key(value) in ANY_VALUES


@dataclass(frozen=True)
class DomainResolution:
    """Outcome of resolving a user supplied domain.

    ``status`` is one of ``"any"`` (no filter), ``"matched"`` or ``"unknown"``.
    ``key`` is the canonical ``domain_key`` used to filter projects and ``name``
    the display name taken from the dataset.
    """

    status: str
    key: str = ""
    name: Optional[str] = None
    requested: str = ""

    @property
    def is_filter(self) -> bool:
        return self.status in ("matched", "unknown")


class DomainResolver:
    """Resolve free-text user domains against the domains present in the data."""

    def __init__(self, known_domains: Iterable[str]):
        counts: Counter[str] = Counter()
        spellings: dict[str, Counter[str]] = {}
        for raw in known_domains:
            key = domain_key(raw)
            if not key or key in ANY_VALUES:
                continue
            counts[key] += 1
            spellings.setdefault(key, Counter())[str(raw).strip()] += 1

        # key -> most common spelling in the data (stable display name)
        self._display: dict[str, str] = {
            key: sorted(variants.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            for key, variants in spellings.items()
        }

        self._lookup: dict[str, str] = {}
        for key in self._display:
            self._register(key, key)
            self._register(compact_key(key), key)

        for canonical, aliases in DOMAIN_ALIASES.items():
            target = domain_key(canonical)
            if target not in self._display:
                continue  # alias for a domain this dataset does not contain
            for alias in aliases:
                self._register(domain_key(alias), target)
                self._register(compact_key(alias), target)

    def _register(self, token: str, target: str) -> None:
        if token and token not in self._lookup:
            self._lookup[token] = target

    @property
    def domains(self) -> list[str]:
        """Display names of every known domain, alphabetically."""
        return sorted(self._display.values(), key=str.casefold)

    def display_name(self, key: str) -> Optional[str]:
        return self._display.get(key)

    def resolve(self, value) -> DomainResolution:
        """Map user input to a canonical domain (see module docstring)."""
        requested = "" if _is_missing(value) else str(value).strip()
        key = domain_key(requested)

        if key in ANY_VALUES:
            return DomainResolution(status="any", requested=requested)

        target = self._lookup.get(key) or self._lookup.get(key.replace(" ", ""))
        if target is None:
            return DomainResolution(status="unknown", requested=requested)

        return DomainResolution(
            status="matched",
            key=target,
            name=self._display[target],
            requested=requested,
        )
