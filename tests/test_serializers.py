import unittest
from datetime import date

import pandas as pd

from tests.helpers import make_projects, real_projects
from src.serializers import build_filter_options, project_detail_dict, project_summary_dict, split_interests, timeline_for


class InterestTests(unittest.TestCase):
    def test_multiword_interests_are_not_split_into_words(self):
        row = real_projects().iloc[0]
        self.assertIn("AI Agents", split_interests(row["interests"]))
        self.assertNotIn("Agents", split_interests(row["interests"]))  # old API returned "AI", "Agents"

    def test_case_insensitive_dedupe_keeps_order(self):
        self.assertEqual(split_interests("Environment|AI Agents|environment|ai agents|beginner"),
                         ["Environment", "AI Agents", "beginner"])

    def test_legacy_space_separated_format_still_works(self):
        self.assertEqual(split_interests("education prediction analytics"), ["education", "prediction", "analytics"])
        self.assertEqual(split_interests("nlp, finance; health care"), ["nlp", "finance", "health care"])

    def test_empty(self):
        for v in ("", None, float("nan")):
            self.assertEqual(split_interests(v), [])


class OptionsTests(unittest.TestCase):
    def test_orders_levels_and_durations_logically(self):
        opts = build_filter_options(real_projects())
        self.assertEqual(opts["skill_levels"], ["Beginner", "Intermediate", "Advanced"])
        self.assertEqual(opts["available_times"], ["1-3 Days", "4-7 Days", "8-15 Days", "16-30 Days", "1-3 Months"])
        self.assertEqual(len(opts["domains"]), 22)
        self.assertEqual(opts["domains"], sorted(opts["domains"]))
        self.assertIn("Python", opts["preferred_languages"])

    def test_blank_values_and_spelling_variants_removed(self):
        df = make_projects(dict(domain="Robotics", skill_level="", available_time="", preferred_language=""),
                           dict(domain="robotics"), dict(domain="Robotics"))
        opts = build_filter_options(df)
        self.assertEqual(opts["domains"], ["Robotics"])
        self.assertEqual(opts["skill_levels"], ["Beginner"])
        self.assertNotIn("", opts["available_times"])
        self.assertNotIn("", opts["preferred_languages"])

    def test_empty_frame(self):
        opts = build_filter_options(pd.DataFrame())
        self.assertEqual(opts, {"domains": [], "skill_levels": [], "available_times": [], "preferred_languages": []})

    def test_every_option_domain_is_selectable_by_the_engine(self):
        from tests.helpers import real_engine
        from src.recommender import UserQuery
        for d in build_filter_options(real_projects())["domains"]:
            self.assertEqual(real_engine().resolver.resolve(d).name, d)


class ShapeTests(unittest.TestCase):
    SUMMARY_KEYS = {"project_id", "title", "domain", "skill_level", "available_time", "preferred_language",
                    "description", "match_score", "match_percentage", "timeline"}
    DETAIL_KEYS = {"project_id", "title", "domain", "skill_level", "interests", "available_time", "preferred_language",
                   "description", "learning_roadmap", "required_skills", "required_libraries", "free_datasets",
                   "free_apis", "learning_resources", "future_scope", "timeline"}

    def test_summary_shape_and_rounding(self):
        row = real_projects().iloc[0].copy()
        row["match_score"] = 0.123456789
        out = project_summary_dict(row, timeline_for(row, date(2026, 3, 1)))
        self.assertEqual(set(out), self.SUMMARY_KEYS)
        self.assertEqual((out["match_score"], out["match_percentage"]), (0.1235, 12.35))
        self.assertIsInstance(out["project_id"], str)

    def test_scores_are_clamped(self):
        row = real_projects().iloc[0].copy()
        for raw, expected in ((1.7, 1.0), (-0.2, 0.0), (None, 0.0)):
            row["match_score"] = raw
            self.assertEqual(project_summary_dict(row)["match_score"], expected)

    def test_detail_shape_and_list_fields(self):
        row = real_projects().iloc[0]
        out = project_detail_dict(row, timeline_for(row, date(2026, 3, 1)))
        self.assertEqual(set(out), self.DETAIL_KEYS)
        for key in ("learning_roadmap", "required_skills", "required_libraries", "free_datasets", "free_apis",
                    "learning_resources", "future_scope", "interests"):
            self.assertIsInstance(out[key], list)
            self.assertTrue(all(isinstance(i, str) for i in out[key]))
        self.assertEqual(out["timeline"]["estimated_duration"]["label"], row["available_time"])

    def test_row_missing_columns_is_safe(self):
        out = project_detail_dict(pd.Series({"project_id": "1", "title": "t"}))
        self.assertEqual(out["domain"], "")
        self.assertEqual(out["required_skills"], [])


if __name__ == "__main__":
    unittest.main()
