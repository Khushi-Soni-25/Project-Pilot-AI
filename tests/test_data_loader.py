import io
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from tests.helpers import DATA_PATH, make_projects, real_projects
from src.data_loader import clean_projects, load_projects, normalize_project_dataframe


class LoaderTests(unittest.TestCase):
    def test_shipped_dataset_loads_cleanly(self):
        df = real_projects()
        self.assertEqual(len(df), 3300)
        self.assertEqual(df["project_id"].nunique(), 3300)
        self.assertFalse((df == "nan").any().any())
        self.assertFalse((df["title"] == "").any())

    def test_csv_with_empty_cells_does_not_leak_nan_text(self):
        csv = io.StringIO(
            "project_id,title,domain,skill_level,interests,available_time,preferred_language,description,"
            "learning_roadmap,required_skills,required_libraries,free_datasets,free_apis,learning_resources,future_scope\n"
            "X1,Test,Machine Learning,Beginner,,2-3 weeks,Python,,,,,,,,\n")
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "p.csv"
            path.write_text(csv.getvalue(), encoding="utf-8")
            row = load_projects(path).iloc[0]
        for column in ("learning_roadmap", "required_skills", "future_scope", "description", "interests"):
            self.assertEqual(row[column], "", column)  # used to be the text "nan"

    def test_json_without_link_columns_no_longer_crashes(self):
        record = {"project_id": "A", "project_name": "N", "domain": "Robotics", "difficulty_level": "Beginner",
                  "estimated_completion_time": "1-3 Days", "programming_languages": "Python",
                  "short_description": "d", "dataset_name": "DS", "api_name": "API",  # no dataset_link / api_link
                  "interest_category": "Finance", "required_skills": ["a"], "required_libraries": ["b"],
                  "learning_roadmap": ["c"], "future_scope": ["d"]}
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "p.json"
            path.write_text(json.dumps({"projects": [record]}), encoding="utf-8")
            row = load_projects(path).iloc[0]
        self.assertEqual(row["free_datasets"], "DS - Not applicable")
        self.assertEqual(row["free_apis"], "API - Not applicable")

    def test_bad_json_shape_is_a_clear_error(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "p.json"
            path.write_text(json.dumps({"projects": {"a": 1}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_projects(path)

    def test_missing_file_and_missing_columns(self):
        with self.assertRaises(FileNotFoundError):
            load_projects("/no/such/file.json")
        with self.assertRaises(ValueError):
            normalize_project_dataframe(pd.DataFrame({"title": ["x"]}))


class CleanTests(unittest.TestCase):
    def test_markers_whitespace_and_none(self):
        df = make_projects(dict(title="  A  ", description="None"), dict(title="B", description="null"),
                           dict(title="C", description=None), dict(title="D", description=float("nan")))
        out = clean_projects(df)
        self.assertEqual(out["title"].tolist(), ["A", "B", "C", "D"])
        self.assertEqual(out["description"].tolist(), ["", "", "", ""])

    def test_rows_without_id_or_title_dropped(self):
        df = make_projects(dict(title="ok"), dict(title=""), dict(title="x"))
        df.loc[2, "project_id"] = ""
        self.assertEqual(clean_projects(df)["title"].tolist(), ["ok"])

    def test_duplicate_ids_case_insensitive_keep_first(self):
        df = make_projects(dict(title="first"), dict(title="second"))
        df.loc[1, "project_id"] = df.loc[0, "project_id"].lower()
        df.loc[0, "project_id"] = df.loc[0, "project_id"].upper()
        self.assertEqual(clean_projects(df)["title"].tolist(), ["first"])

    def test_identical_content_different_id_dropped_but_distinct_interests_kept(self):
        df = make_projects(dict(title="A", interests="x"), dict(title="A", interests="x"), dict(title="A", interests="y"))
        self.assertEqual(clean_projects(df)["interests"].tolist(), ["x", "y"])

    def test_idempotent_and_empty_inputs(self):
        once = clean_projects(real_projects())
        pd.testing.assert_frame_equal(once, clean_projects(once))
        for empty in (None, pd.DataFrame()):
            self.assertTrue(clean_projects(empty).empty)


if __name__ == "__main__":
    unittest.main()
