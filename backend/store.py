"""Cached access to the project data and the recommendation engine.

Before this module every request reloaded and re-normalised the whole dataset,
refitted TF-IDF over all 3,300 projects and, whenever MongoDB was unreachable,
also waited out the 2 second server-selection timeout. Now the prepared engine is
kept in memory and refreshed on a short TTL.

Behaviour is otherwise unchanged: MongoDB is preferred, the local JSON dataset is
the fallback, and an unreachable or empty MongoDB never breaks a request.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Callable, Optional

import pandas as pd

from src.recommender import RecommendationEngine

logger = logging.getLogger(__name__)


def _env_seconds(name: str, default: float) -> float:
    try:
        return max(float(os.getenv(name, default)), 0.0)
    except ValueError:
        return default


DEFAULT_TTL_SECONDS = _env_seconds("PROJECT_CACHE_TTL_SECONDS", 60.0)
DEFAULT_MONGO_RETRY_SECONDS = _env_seconds("MONGO_RETRY_SECONDS", 60.0)


class ProjectStore:
    """Serve a ready-to-use ``RecommendationEngine`` from MongoDB or JSON."""

    def __init__(
        self,
        mongo_loader: Callable[[], pd.DataFrame],
        json_loader: Callable[[], pd.DataFrame],
        *,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        mongo_retry_seconds: float = DEFAULT_MONGO_RETRY_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._mongo_loader = mongo_loader
        self._json_loader = json_loader
        self._ttl = ttl_seconds
        self._mongo_retry = mongo_retry_seconds
        self._clock = clock

        self._lock = threading.Lock()
        self._engine: Optional[RecommendationEngine] = None
        self._loaded_at = 0.0
        self._mongo_down_until = 0.0
        self.source = "none"  # "mongodb" | "json" | "none"

    def invalidate(self) -> None:
        """Force the next ``get_engine`` call to reload."""
        with self._lock:
            self._engine = None

    def get_engine(self) -> RecommendationEngine:
        """Return the cached engine, reloading it when the TTL has expired."""
        with self._lock:
            now = self._clock()
            if self._engine is not None and now - self._loaded_at < self._ttl:
                return self._engine

            try:
                engine, source = self._build(now)
            except Exception:
                if self._engine is None:
                    raise
                # Keep serving the last good data and try again after the TTL.
                logger.exception("Project reload failed; serving previously loaded data")
                self._loaded_at = now
                return self._engine

            self._engine, self.source, self._loaded_at = engine, source, now
            return engine

    def _build(self, now: float) -> tuple[RecommendationEngine, str]:
        if now >= self._mongo_down_until:
            try:
                frame = self._mongo_loader()
                if frame is not None and not frame.empty:
                    return RecommendationEngine(frame), "mongodb"
            except Exception as exc:  # unreachable, not installed, bad schema ...
                self._mongo_down_until = now + self._mongo_retry
                logger.warning(
                    "MongoDB unavailable (%s); using the JSON dataset for %.0fs",
                    exc,
                    self._mongo_retry,
                )

        return RecommendationEngine(self._json_loader()), "json"
