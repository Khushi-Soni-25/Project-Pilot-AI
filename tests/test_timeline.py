import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from tests.helpers import ROOT, real_projects
from src.timeline import (
    Duration, add_months, build_timeline, duration_sort_key, parse_date_input, parse_duration,
    resolve_deadline, resolve_start_date, time_budget_days, utc_today,
)


class ParseDurationTests(unittest.TestCase):
    def test_every_duration_in_the_dataset_parses(self):
        labels = set(real_projects()["available_time"])
        self.assertEqual(labels, {"1-3 Days", "4-7 Days", "8-15 Days", "16-30 Days", "1-3 Months"})
        for label in labels:
            parsed = parse_duration(label)
            self.assertIsNotNone(parsed, label)
            self.assertEqual(parsed.label, label)

    def test_values(self):
        d = parse_duration("4-7 Days")
        self.assertEqual((d.min_days, d.max_days, d.unit), (4, 7, "days"))
        m = parse_duration("1-3 Months")
        self.assertEqual((m.min_days, m.max_days), (30, 90))
        w = parse_duration("2-3 weeks")  # legacy CSV / Streamlit vocabulary
        self.assertEqual((w.min_days, w.max_days, w.label), (14, 21, "2-3 Weeks"))

    def test_flexible_input_formats(self):
        for text in ("4 - 7 days", "4–7 DAYS", "4 to 7 days", "  4-7   Days  "):
            self.assertEqual(parse_duration(text), Duration(4, 7, "days"), text)
        self.assertEqual(parse_duration("3 days"), Duration(3, 3, "days"))
        self.assertEqual(parse_duration("1 week").label, "1 Weeks")  # single value keeps unit plural
        self.assertEqual(parse_duration("1 week").max_days, 7)

    def test_garbage_is_rejected_not_guessed(self):
        for bad in (None, "", "soon", "7-4 days", "0 days", "0-3 days", "-3 days", "3-5", "5 years",
                    "a few days", 5, 3.5, ["4-7 days"], float("nan"), "4-7 days extra"):
            self.assertIsNone(parse_duration(bad), repr(bad))

    def test_sort_order_is_by_length_not_text(self):
        shuffled = ["1-3 Months", "16-30 Days", "4-7 Days", "8-15 Days", "1-3 Days", "weird"]
        self.assertEqual(
            sorted(shuffled, key=duration_sort_key),
            ["1-3 Days", "4-7 Days", "8-15 Days", "16-30 Days", "1-3 Months", "weird"],
        )
        # the old text sort put "1-3 Months" ahead of "4-7 Days":
        self.assertNotEqual(sorted(shuffled)[:3], sorted(shuffled, key=duration_sort_key)[:3])


class CompletionDateTests(unittest.TestCase):
    def test_days(self):
        self.assertEqual(parse_duration("4-7 Days").completion_window(date(2026, 3, 1)),
                         (date(2026, 3, 5), date(2026, 3, 8)))

    def test_weeks(self):
        self.assertEqual(parse_duration("2-3 weeks").completion_window(date(2026, 3, 1)),
                         (date(2026, 3, 15), date(2026, 3, 22)))

    def test_months_are_calendar_months(self):
        self.assertEqual(parse_duration("1-3 Months").completion_window(date(2026, 3, 1)),
                         (date(2026, 4, 1), date(2026, 6, 1)))

    def test_month_end_clamping_and_leap_years(self):
        self.assertEqual(add_months(date(2027, 1, 31), 1), date(2027, 2, 28))
        self.assertEqual(add_months(date(2028, 1, 31), 1), date(2028, 2, 29))  # leap year
        self.assertEqual(add_months(date(2026, 8, 31), 1), date(2026, 9, 30))
        self.assertEqual(add_months(date(2026, 5, 31), 3), date(2026, 8, 31))

    def test_year_rollover(self):
        self.assertEqual(parse_duration("1-3 Months").completion_window(date(2026, 12, 15)),
                         (date(2027, 1, 15), date(2027, 3, 15)))
        self.assertEqual(parse_duration("16-30 Days").completion_window(date(2026, 12, 20)),
                         (date(2027, 1, 5), date(2027, 1, 19)))

    def test_leap_day_crossing(self):
        self.assertEqual(parse_duration("1-3 Days").completion_window(date(2028, 2, 28)),
                         (date(2028, 2, 29), date(2028, 3, 2)))
        self.assertEqual(parse_duration("1-3 Days").completion_window(date(2027, 2, 28)),
                         (date(2027, 3, 1), date(2027, 3, 3)))

    def test_earliest_never_after_latest_for_every_dataset_duration(self):
        for label in set(real_projects()["available_time"]):
            for offset in range(0, 800, 37):
                start = date(2026, 1, 1) + timedelta(days=offset)
                lo, hi = parse_duration(label).completion_window(start)
                self.assertLess(start, lo)
                self.assertLessEqual(lo, hi)


class DateAndTimezoneTests(unittest.TestCase):
    def test_utc_today_uses_utc_not_local_time(self):
        late_est = datetime(2026, 3, 1, 23, 30, tzinfo=timezone(timedelta(hours=-5)))  # = Mar 2, 04:30 UTC
        self.assertEqual(utc_today(late_est), date(2026, 3, 2))
        early_ist = datetime(2026, 3, 1, 1, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))  # = Feb 28 19:30 UTC
        self.assertEqual(utc_today(early_ist), date(2026, 2, 28))
        self.assertEqual(utc_today(datetime(2026, 3, 1, 23, 59)), date(2026, 3, 1))  # naive = UTC

    def test_parse_date_input_formats(self):
        self.assertEqual(parse_date_input("2026-03-01"), date(2026, 3, 1))
        self.assertEqual(parse_date_input(" 2026-03-01 "), date(2026, 3, 1))
        self.assertEqual(parse_date_input("2026-03-01T09:30:00Z"), date(2026, 3, 1))
        self.assertEqual(parse_date_input("2026-03-01T23:30:00-05:00"), date(2026, 3, 2))
        self.assertEqual(parse_date_input("2026-03-01T01:00:00+05:30"), date(2026, 2, 28))
        self.assertEqual(parse_date_input("2026-03-01T10:00:00"), date(2026, 3, 1))
        self.assertEqual(parse_date_input(date(2026, 3, 1)), date(2026, 3, 1))
        self.assertEqual(parse_date_input(datetime(2026, 3, 1, 23, 0, tzinfo=timezone(timedelta(hours=-5)))),
                         date(2026, 3, 2))

    def test_empty_means_not_given(self):
        for value in (None, "", "   "):
            self.assertIsNone(parse_date_input(value))

    def test_invalid_dates_raise_named_errors(self):
        for bad in ("03/01/2026", "2026-13-01", "2026-02-30", "tomorrow", "2026-3-1", 20260301, "2026-03-01 25:00"):
            with self.assertRaises(ValueError, msg=repr(bad)) as ctx:
                parse_date_input(bad, "deadline")
            self.assertIn("deadline", str(ctx.exception))

    def test_start_date_defaults_to_injected_today(self):
        now = datetime(2026, 11, 22, 8, 0, tzinfo=timezone.utc)
        self.assertEqual(resolve_start_date(None, now), date(2026, 11, 22))
        self.assertEqual(resolve_start_date("", now), date(2026, 11, 22))
        self.assertEqual(resolve_start_date("2026-12-01", now), date(2026, 12, 1))

    def test_deadline_cannot_precede_start(self):
        start = date(2026, 3, 10)
        self.assertEqual(resolve_deadline("2026-03-10", start), date(2026, 3, 10))  # same day is allowed
        self.assertIsNone(resolve_deadline(None, start))
        with self.assertRaises(ValueError):
            resolve_deadline("2026-03-09", start)


class TimeBudgetTests(unittest.TestCase):
    def test_available_time_upper_bound_wins(self):
        self.assertEqual(time_budget_days("8-15 Days"), 15)
        self.assertEqual(time_budget_days("1-3 Months"), 90)
        self.assertEqual(time_budget_days("2-3 weeks"), 21)

    def test_deadline_used_only_when_no_available_time(self):
        start, deadline = date(2026, 3, 1), date(2026, 3, 11)
        self.assertEqual(time_budget_days("", start, deadline), 10)
        self.assertEqual(time_budget_days("4-7 Days", start, deadline), 7)  # explicit choice wins
        self.assertEqual(time_budget_days("garbage", start, deadline), 10)

    def test_nothing_stated(self):
        self.assertIsNone(time_budget_days(""))
        self.assertIsNone(time_budget_days("Any"))
        self.assertIsNone(time_budget_days(None, date(2026, 1, 1), None))


class BuildTimelineTests(unittest.TestCase):
    START = date(2026, 3, 1)

    def test_estimate_only(self):
        t = build_timeline("4-7 Days", self.START)
        self.assertEqual(t["timezone"], "UTC")
        self.assertEqual(t["start_date"], "2026-03-01")
        self.assertEqual(t["estimated_duration"], {"label": "4-7 Days", "min_days": 4, "max_days": 7})
        self.assertEqual(t["estimated_completion"], {"earliest": "2026-03-05", "latest": "2026-03-08"})
        self.assertIsNone(t["deadline"])
        self.assertIsNone(t["days_until_deadline"])
        self.assertIsNone(t["fits_deadline"])

    def test_deadline_is_kept_separate_from_the_estimate(self):
        without = build_timeline("8-15 Days", self.START)
        with_deadline = build_timeline("8-15 Days", self.START, date(2026, 3, 20))
        self.assertEqual(without["estimated_completion"], with_deadline["estimated_completion"])
        self.assertEqual(without["estimated_duration"], with_deadline["estimated_duration"])
        self.assertEqual(with_deadline["deadline"], "2026-03-20")
        self.assertEqual(with_deadline["days_until_deadline"], 19)
        self.assertNotEqual(with_deadline["deadline"], with_deadline["estimated_completion"]["latest"])

    def test_fits_deadline_uses_worst_case_and_is_inclusive(self):
        # 8-15 days from Mar 1 -> latest Mar 16
        self.assertTrue(build_timeline("8-15 Days", self.START, date(2026, 3, 16))["fits_deadline"])
        self.assertFalse(build_timeline("8-15 Days", self.START, date(2026, 3, 15))["fits_deadline"])
        self.assertTrue(build_timeline("1-3 Days", self.START, date(2026, 3, 4))["fits_deadline"])
        self.assertFalse(build_timeline("1-3 Days", self.START, date(2026, 3, 3))["fits_deadline"])

    def test_month_duration_against_deadline(self):
        t = build_timeline("1-3 Months", date(2026, 3, 1), date(2026, 5, 31))
        self.assertEqual(t["estimated_completion"]["latest"], "2026-06-01")
        self.assertFalse(t["fits_deadline"])
        self.assertTrue(build_timeline("1-3 Months", date(2026, 3, 1), date(2026, 6, 1))["fits_deadline"])

    def test_unparseable_duration_yields_no_estimate_and_no_guess(self):
        for bad in ("", "soon", None):
            t = build_timeline(bad, self.START, date(2026, 3, 20))
            self.assertIsNone(t["estimated_duration"])
            self.assertIsNone(t["estimated_completion"])
            self.assertIsNone(t["fits_deadline"])
            self.assertEqual(t["deadline"], "2026-03-20")  # the real deadline is still reported

    def test_dates_are_iso_strings(self):
        t = build_timeline("1-3 Months", date(2026, 12, 31), date(2027, 6, 1))
        for value in (t["start_date"], t["deadline"], *t["estimated_completion"].values()):
            self.assertRegex(value, r"^\d{4}-\d{2}-\d{2}$")

    def test_deterministic(self):
        a = build_timeline("16-30 Days", self.START, date(2026, 4, 1))
        b = build_timeline("16-30 Days", self.START, date(2026, 4, 1))
        self.assertEqual(a, b)


class NoRandomnessTests(unittest.TestCase):
    def test_no_random_in_backend_sources(self):
        for folder in ("src", "backend"):
            for path in Path(ROOT / folder).glob("*.py"):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("import random", text, path.name)
                self.assertNotIn("np.random", text, path.name)
                self.assertNotIn("numpy.random", text, path.name)


if __name__ == "__main__":
    unittest.main()
