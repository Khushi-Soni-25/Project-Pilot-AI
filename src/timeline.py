"""Timeline maths for ProjectPilot AI.

Audit summary (what the backend had before)
-------------------------------------------
The dataset carries only a free-text *estimated duration* per project
(``"4-7 Days"``, ``"1-3 Months"``; the legacy CSV used ``"2-3 weeks"``). There were
no start dates, deadlines or completion dates anywhere, and the duration text was
only ever fed to TF-IDF, where digits were discarded, so "1-3 Days" and
"4-7 Days" were indistinguishable.

Rules implemented here
----------------------
* Durations are parsed, never guessed. Unparseable text yields ``None``.
* Nothing is random and nothing depends on the host time zone. "Today" is the
  current **UTC** calendar date unless a caller injects ``now``.
* Dates are serialised as ISO-8601 ``YYYY-MM-DD`` strings.
* An *estimated duration* (from the dataset) and a *deadline* (an actual date
  supplied by the caller) are separate values. A deadline is never derived from
  a duration, and a duration is never derived from a deadline.
* Estimated completion = start date + duration. Day/week durations add that many
  elapsed days; month durations add calendar months (clamped to month end).
  For *comparing* durations across units only, a month counts as 30 days.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

DAYS_PER_WEEK = 7
DAYS_PER_MONTH_FOR_COMPARISON = 30

_UNIT_NORMAL = {
    "day": "days",
    "days": "days",
    "week": "weeks",
    "weeks": "weeks",
    "month": "months",
    "months": "months",
}

_DURATION_RE = re.compile(
    r"""^\s*
        (?P<lo>\d{1,4})
        (?:\s*(?:-|–|—|to)\s*(?P<hi>\d{1,4}))?
        \s*(?P<unit>days?|weeks?|months?)
        \s*$""",
    re.IGNORECASE | re.VERBOSE,
)


@dataclass(frozen=True)
class Duration:
    """A parsed estimated duration such as ``4-7 Days``."""

    min_value: int
    max_value: int
    unit: str  # "days" | "weeks" | "months"

    @property
    def label(self) -> str:
        """Canonical label: ``"4-7 Days"``, ``"2 Weeks"``."""
        span = (
            str(self.min_value)
            if self.min_value == self.max_value
            else f"{self.min_value}-{self.max_value}"
        )
        return f"{span} {self.unit.capitalize()}"

    @property
    def min_days(self) -> int:
        return self.min_value * _days_per_unit(self.unit)

    @property
    def max_days(self) -> int:
        return self.max_value * _days_per_unit(self.unit)

    def completion_window(self, start: date) -> tuple[date, date]:
        """Earliest and latest estimated completion dates when starting on ``start``."""
        return (
            _advance(start, self.min_value, self.unit),
            _advance(start, self.max_value, self.unit),
        )


def _days_per_unit(unit: str) -> int:
    if unit == "weeks":
        return DAYS_PER_WEEK
    if unit == "months":
        return DAYS_PER_MONTH_FOR_COMPARISON
    return 1


def parse_duration(value: Any) -> Optional[Duration]:
    """Parse ``"4-7 Days"``, ``"2 weeks"``, ``"1 to 3 months"``; else ``None``.

    Zero, reversed ranges (``"7-4 days"``), unknown units and non-text values are
    rejected rather than repaired.
    """
    if value is None or not isinstance(value, str):
        return None
    match = _DURATION_RE.match(value)
    if not match:
        return None

    low = int(match.group("lo"))
    high = int(match.group("hi")) if match.group("hi") is not None else low
    if low <= 0 or high < low:
        return None

    return Duration(low, high, _UNIT_NORMAL[match.group("unit").lower()])


def duration_sort_key(value: Any) -> tuple:
    """Sort key ordering durations by length; unparseable values sort last."""
    parsed = parse_duration(value)
    if parsed is None:
        return (1, 0, 0, str(value))
    return (0, parsed.min_days, parsed.max_days, parsed.label)


def add_months(start: date, months: int) -> date:
    """Calendar-aware month addition (Jan 31 + 1 month -> Feb 28/29)."""
    index = start.year * 12 + (start.month - 1) + months
    year, month = divmod(index, 12)
    month += 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _advance(start: date, amount: int, unit: str) -> date:
    if unit == "months":
        return add_months(start, amount)
    return start + timedelta(days=amount * _days_per_unit(unit))


# --------------------------------------------------------------------------- #
# Dates and time zones
# --------------------------------------------------------------------------- #


def utc_today(now: Optional[datetime] = None) -> date:
    """Current calendar date in UTC. ``now`` may be injected (and may be naive/aware)."""
    moment = now if now is not None else datetime.now(timezone.utc)
    if moment.tzinfo is not None:
        moment = moment.astimezone(timezone.utc)
    return moment.date()


def parse_date_input(value: Any, field: str = "date") -> Optional[date]:
    """Parse a caller supplied date into a UTC calendar date.

    Accepts ``None``/``""`` (-> ``None``), ``date``, ``datetime`` and ISO-8601
    strings (``2026-03-01``, ``2026-03-01T09:30:00Z``, ``...+05:30``). Aware
    datetimes are converted to UTC before taking the date; naive datetimes are
    taken as UTC. Anything else raises ``ValueError`` naming ``field``.
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return utc_today(value)
    if isinstance(value, date):
        return value

    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 date such as 2026-03-01")

    text = value.strip()
    if not text:
        return None

    try:
        if len(text) == 10:
            return date.fromisoformat(text)
        if text.endswith(("Z", "z")):
            text = text[:-1] + "+00:00"
        return utc_today(datetime.fromisoformat(text))
    except ValueError:
        raise ValueError(
            f"{field} must be an ISO-8601 date such as 2026-03-01 (got {value!r})"
        ) from None


def resolve_start_date(start_date: Any = None, now: Optional[datetime] = None) -> date:
    """The plan start: the caller's date, otherwise today's UTC date."""
    parsed = parse_date_input(start_date, "start_date")
    return parsed if parsed is not None else utc_today(now)


def resolve_deadline(deadline: Any, start: date) -> Optional[date]:
    """Validate an actual deadline. It may not precede the start date."""
    parsed = parse_date_input(deadline, "deadline")
    if parsed is not None and parsed < start:
        raise ValueError("deadline must not be before start_date")
    return parsed


def time_budget_days(
    available_time: Any,
    start: Optional[date] = None,
    deadline: Optional[date] = None,
) -> Optional[int]:
    """How many days the user can spend, or ``None`` when nothing was stated.

    The selected *available time* wins (its upper bound is the budget, e.g.
    "8-15 Days" -> 15). Without it, an explicit deadline gives the days between
    ``start`` and ``deadline``.
    """
    duration = parse_duration(available_time)
    if duration is not None:
        return duration.max_days
    if deadline is not None and start is not None:
        return max((deadline - start).days, 0)
    return None


# --------------------------------------------------------------------------- #
# Timeline payload
# --------------------------------------------------------------------------- #


def build_timeline(
    duration_label: Any,
    start: date,
    deadline: Optional[date] = None,
) -> dict:
    """Build the timeline block returned with each project.

    ``estimated_*`` keys come only from the dataset's duration. ``deadline`` and
    ``days_until_deadline`` come only from the caller. ``fits_deadline`` compares
    the two using the *latest* estimated completion (worst case) and is ``None``
    whenever either side is unknown.
    """
    duration = parse_duration(duration_label)

    block: dict = {
        "timezone": "UTC",
        "start_date": start.isoformat(),
        "estimated_duration": None,
        "estimated_completion": None,
        "deadline": deadline.isoformat() if deadline else None,
        "days_until_deadline": (deadline - start).days if deadline else None,
        "fits_deadline": None,
    }

    if duration is None:
        return block

    earliest, latest = duration.completion_window(start)
    block["estimated_duration"] = {
        "label": duration.label,
        "min_days": duration.min_days,
        "max_days": duration.max_days,
    }
    block["estimated_completion"] = {
        "earliest": earliest.isoformat(),
        "latest": latest.isoformat(),
    }
    if deadline is not None:
        block["fits_deadline"] = latest <= deadline

    return block
