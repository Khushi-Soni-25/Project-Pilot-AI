"""Handler-level tests for backend/app.py.

With real FastAPI/pydantic installed these use the real models. Without them
(offline sandbox) tests/stubs.py supplies stand-ins that execute the same code
paths but do not validate types; HTTP-level tests are then skipped.
"""

import unittest
from datetime import date

from tests import stubs

STUBBED = stubs.install_if_needed()

from tests.helpers import DATA_PATH, make_projects  # noqa: E402
from backend import app as backend_app  # noqa: E402
from backend.schemas import RecommendationRequest  # noqa: E402
from backend.store import ProjectStore  # noqa: E402
from src.data_loader import load_projects  # noqa: E402
from fastapi import HTTPException  # noqa: E402


def dump(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, list):
        return [dump(o) for o in obj]
    if isinstance(obj, dict):
        return {k: dump(v) for k, v in obj.items()}
    if hasattr(obj, "__dict__") and not isinstance(obj, (str, int, float)):
        return {k: dump(v) for k, v in vars(obj).items()}
    return obj


def mongo_down():
    raise ConnectionError("mongo unavailable in tests")


def use_store(json_loader):
    backend_app.project_store = ProjectStore(mongo_down, json_loader, ttl_seconds=3600)


class ApiBase(unittest.TestCase):
    _frame = None

    @classmethod
    def setUpClass(cls):
        use_store(lambda: load_projects(DATA_PATH))

    def rec(self, **kw):
        return dump(backend_app.recommend(RecommendationRequest(**kw)))


class RecommendEndpointTests(ApiBase):
    def test_frontend_payload_returns_expected_structure(self):
        # exactly what frontend/js/app.js sends
        out = self.rec(domain="Machine Learning", skill_level="Beginner", interests="regression dashboard",
                       available_time="8-15 Days", preferred_language="Python", top_n=5)
        self.assertEqual({"user_profile", "total_projects", "recommendations", "resolved_domain"}, set(out))
        self.assertEqual(out["total_projects"], 3300)
        self.assertEqual(out["resolved_domain"], "Machine Learning")
        self.assertEqual(len(out["recommendations"]), 5)
        for item in out["recommendations"]:
            for key in ("project_id", "title", "domain", "skill_level", "available_time", "preferred_language",
                        "description", "match_score", "match_percentage"):
                self.assertIn(key, item)
            self.assertEqual(item["domain"], "Machine Learning")
            self.assertAlmostEqual(item["match_percentage"], item["match_score"] * 100, delta=0.01)
        pct = [i["match_percentage"] for i in out["recommendations"]]
        self.assertEqual(pct, sorted(pct, reverse=True))

    def test_every_domain_via_the_api(self):
        domains = backend_app.get_filter_options()
        for d in dump(domains)["domains"]:
            out = self.rec(domain=d, skill_level="Any", interests="python", available_time="Any",
                           preferred_language="Any", top_n=10)
            self.assertGreater(len(out["recommendations"]), 0, d)
            self.assertEqual({r["domain"] for r in out["recommendations"]}, {d})

    def test_titles_are_unique(self):
        out = self.rec(domain="Web Development", skill_level="Beginner", interests="api", top_n=10)
        titles = [r["title"] for r in out["recommendations"]]
        self.assertEqual(len(titles), len(set(titles)))

    def test_any_everywhere(self):
        out = self.rec(domain="Any", skill_level="Any", interests="dashboard", available_time="Any", preferred_language="Any")
        self.assertGreater(len(out["recommendations"]), 0)
        self.assertIsNone(out["resolved_domain"])

    def test_unknown_domain_gives_empty_list_not_other_domains(self):
        out = self.rec(domain="Underwater Basket Weaving", interests="python")
        self.assertEqual(out["recommendations"], [])
        self.assertIsNone(out["resolved_domain"])

    def test_alias_and_null_fields_are_accepted(self):
        out = self.rec(domain="ml", skill_level=None, interests="regression", available_time=None,
                       preferred_language=None, skills=None)
        self.assertEqual(out["resolved_domain"], "Machine Learning")
        self.assertGreater(len(out["recommendations"]), 0)

    def test_skills_field_influences_results(self):
        a = self.rec(domain="DevOps", skills="kubernetes, docker", top_n=3)
        b = self.rec(domain="DevOps", skills="", top_n=3, interests="")
        self.assertEqual(len(a["recommendations"]), 3)
        ids_a = [r["project_id"] for r in a["recommendations"]]
        ids_b = [r["project_id"] for r in b["recommendations"]]
        self.assertNotEqual(ids_a, ids_b)  # skills changed the ranking
        for pid in ids_a:
            libs = dump(backend_app.get_project(pid))["required_libraries"]
            self.assertTrue({"Docker", "Kubernetes"} & set(libs), (pid, libs))

    def test_no_signal_returns_empty(self):
        out = self.rec(domain="Any", skill_level="Any", interests="", available_time="Any", preferred_language="Any")
        self.assertEqual(out["recommendations"], [])

    def test_user_profile_text_keeps_previous_meaning(self):
        out = self.rec(domain="Any", skill_level="Beginner", interests="nlp", available_time="Any", preferred_language="Python")
        self.assertEqual(out["user_profile"], "beginner nlp python")


class TimelineEndpointTests(ApiBase):
    def test_default_start_is_today_utc_and_estimates_match_the_dataset_duration(self):
        out = self.rec(domain="Machine Learning", skill_level="Beginner", interests="regression", top_n=5)
        today = backend_app.resolve_start_date().isoformat()
        for r in out["recommendations"]:
            t = r["timeline"]
            self.assertEqual(t["start_date"], today)
            self.assertEqual(t["estimated_duration"]["label"], r["available_time"])
            self.assertIsNone(t["deadline"])
            self.assertIsNone(t["fits_deadline"])

    def test_explicit_start_and_deadline(self):
        out = self.rec(domain="Machine Learning", skill_level="Beginner", interests="regression", top_n=10,
                       start_date="2026-03-01", deadline="2026-03-10")
        for r in out["recommendations"]:
            t = r["timeline"]
            self.assertEqual((t["start_date"], t["deadline"], t["days_until_deadline"]), ("2026-03-01", "2026-03-10", 9))
            latest = date.fromisoformat(t["estimated_completion"]["latest"])
            self.assertEqual(t["fits_deadline"], latest <= date(2026, 3, 10))
        self.assertTrue({r["timeline"]["fits_deadline"] for r in out["recommendations"]} <= {True, False})

    def test_deadline_alone_sets_the_time_budget(self):
        short = self.rec(domain="Machine Learning", skill_level="Beginner", interests="regression", top_n=3,
                         start_date="2026-03-01", deadline="2026-03-04")  # 3 days
        self.assertTrue(all(r["available_time"] == "1-3 Days" for r in short["recommendations"][:2]))

    def test_bad_dates_return_422_with_readable_detail(self):
        for kw in ({"start_date": "01/03/2026"}, {"deadline": "soon"}, {"start_date": "2026-03-10", "deadline": "2026-03-01"}):
            with self.assertRaises(HTTPException) as ctx:
                self.rec(domain="Robotics", interests="arm", **kw)
            self.assertEqual(ctx.exception.status_code, 422)
            self.assertIsInstance(ctx.exception.detail, str)

    def test_timezone_aware_start_is_converted_to_utc(self):
        out = self.rec(domain="Robotics", interests="robot", skill_level="Beginner", start_date="2026-03-01T23:30:00-05:00")
        self.assertEqual(out["recommendations"][0]["timeline"]["start_date"], "2026-03-02")


class OtherEndpointTests(ApiBase):
    def test_health_options_and_project_detail(self):
        self.assertEqual(dump(backend_app.health_check())["total_projects"], 3300)
        opts = dump(backend_app.get_filter_options())
        self.assertEqual(opts["skill_levels"], ["Beginner", "Intermediate", "Advanced"])
        self.assertEqual(opts["available_times"][0], "1-3 Days")
        detail = dump(backend_app.get_project("ml-beg-006"))  # case-insensitive id
        self.assertEqual(detail["project_id"], "ML-BEG-006")
        self.assertIn("timeline", detail)
        self.assertEqual(detail["timeline"]["estimated_duration"]["label"], detail["available_time"])
        self.assertTrue(all(isinstance(x, str) for x in detail["learning_roadmap"]))

    def test_unknown_project_is_404(self):
        with self.assertRaises(HTTPException) as ctx:
            backend_app.get_project("NOPE-1")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_list_projects(self):
        out = backend_app.list_projects()
        self.assertEqual(len(out), 3300)
        self.assertEqual(len({dump(p)["project_id"] for p in out}), 3300)

    def test_recommended_ids_resolve_via_project_endpoint(self):
        out = self.rec(domain="Cybersecurity", skill_level="Beginner", interests="password", top_n=5)
        for r in out["recommendations"]:
            self.assertEqual(dump(backend_app.get_project(r["project_id"]))["domain"], "Cybersecurity")


class ResilienceTests(unittest.TestCase):
    def tearDown(self):
        use_store(lambda: load_projects(DATA_PATH))

    def test_engine_failure_is_a_safe_500(self):
        def boom():
            raise RuntimeError("secret internal detail")
        use_store(boom)
        with self.assertRaises(HTTPException) as ctx:
            backend_app.recommend(RecommendationRequest(domain="Robotics", interests="x"))
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertNotIn("secret", str(ctx.exception.detail))

    def test_works_with_a_tiny_dataset_and_duplicates(self):
        frame = make_projects(dict(title="Only", description="alpha"), dict(title="Only", description="alpha"))
        use_store(lambda: frame)
        out = dump(backend_app.recommend(RecommendationRequest(domain="ML", interests="alpha")))
        self.assertEqual(out["total_projects"], 1)
        self.assertEqual(len(out["recommendations"]), 1)

    def test_empty_dataset_yields_empty_results_and_options(self):
        import pandas as pd
        use_store(lambda: pd.DataFrame())
        out = dump(backend_app.recommend(RecommendationRequest(domain="ML", interests="alpha")))
        self.assertEqual((out["total_projects"], out["recommendations"]), (0, []))
        self.assertEqual(dump(backend_app.get_filter_options())["domains"], [])

    def test_check_backend_script_still_runs(self):
        import contextlib, io, check_backend
        use_store(lambda: load_projects(DATA_PATH))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            check_backend.main()
        self.assertIn("Backend import: OK", buf.getvalue())


@unittest.skipIf(STUBBED, "real fastapi/httpx not installed")
class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from fastapi.testclient import TestClient
        except Exception as exc:  # httpx missing
            raise unittest.SkipTest(str(exc))
        use_store(lambda: load_projects(DATA_PATH))
        cls.client = TestClient(backend_app.app)

    def test_post_recommend_over_http(self):
        r = self.client.post("/recommend", json={"domain": "Robotics", "skill_level": "Beginner", "interests": "robot",
                                                  "available_time": "Any", "preferred_language": "Any", "top_n": 3})
        self.assertEqual(r.status_code, 200)
        self.assertEqual({x["domain"] for x in r.json()["recommendations"]}, {"Robotics"})

    def test_validation_errors(self):
        self.assertEqual(self.client.post("/recommend", json={"top_n": 99}).status_code, 422)
        self.assertEqual(self.client.post("/recommend", json={"deadline": "nope"}).status_code, 422)

    def test_get_routes(self):
        for path in ("/", "/health", "/options", "/projects/ML-BEG-006"):
            self.assertEqual(self.client.get(path).status_code, 200, path)
        self.assertEqual(self.client.get("/projects/none").status_code, 404)


if __name__ == "__main__":
    unittest.main()
