import unittest
import warnings

import numpy as np
import pandas as pd

from tests.helpers import make_projects, real_engine, real_projects
from src.recommender import (
    RecommendationEngine, UserQuery, analyze_text, build_user_profile, normalize_level, recommend_projects,
)

ENGINE = None


def engine():
    return real_engine()


def ids(result):
    return result.recommendations["project_id"].tolist()


class DomainStrictnessTests(unittest.TestCase):
    """Unrelated domains must never appear, whatever the interests say."""

    def test_each_domain_independently_returns_only_that_domain(self):
        domains = sorted(set(real_projects()["domain"]))
        self.assertEqual(len(domains), 22)
        for domain in domains:
            for level in ("", "Beginner", "Advanced"):
                res = engine().recommend(UserQuery(domain=domain, skill_level=level, interests="python dashboard"), 10)
                df = res.recommendations
                self.assertGreater(len(df), 0, (domain, level))
                self.assertEqual(set(df["domain"]), {domain}, (domain, level))
                self.assertEqual(res.resolution.name, domain)

    def test_adversarial_interests_from_every_other_domain_never_leak(self):
        projects = real_projects()
        domains = sorted(set(projects["domain"]))
        # vocabulary that is distinctive for each domain: its subdomains + its own name
        vocab = {
            d: " ".join(sorted(set(projects[projects.domain == d]["interests"].str.split("|").explode()))) + " " + d
            for d in domains
        }
        checked = 0
        for selected in domains:
            others = " ".join(vocab[d] for d in domains if d != selected)
            for interests in (others, *[vocab[d] for d in domains if d != selected][:6]):
                df = engine().recommend(UserQuery(domain=selected, interests=interests, skills=others[:200]), 10).recommendations
                self.assertTrue(set(df["domain"]) <= {selected}, (selected, set(df["domain"])))
                checked += 1
        self.assertGreater(checked, 150)

    def test_original_failure_case_ml_with_nlp_interests(self):
        df = engine().recommend(UserQuery(domain="Machine Learning", skill_level="Beginner", interests="nlp text sentiment"), 10).recommendations
        self.assertEqual(set(df["domain"]), {"Machine Learning"})  # used to be 10x Natural Language Processing

    def test_aliases_select_the_same_projects_as_the_full_name(self):
        for alias, full in (("ml", "Machine Learning"), ("NLP", "Natural Language Processing"), ("iot", "Internet of Things (IoT)")):
            a = engine().recommend(UserQuery(domain=alias, interests="sensor model"), 8)
            b = engine().recommend(UserQuery(domain=full, interests="sensor model"), 8)
            self.assertEqual(ids(a), ids(b), alias)

    def test_unknown_domain_returns_nothing_instead_of_other_domains(self):
        for domain in ("Quantum Basket Weaving", "Machin Learning", "Learning"):
            res = engine().recommend(UserQuery(domain=domain, interests="python"), 5)
            self.assertTrue(res.recommendations.empty)
            self.assertEqual(res.resolution.status, "unknown")
            self.assertIsNone(res.resolution.name)

    def test_any_spans_domains(self):
        df = engine().recommend(UserQuery(domain="Any", interests="dashboard"), 10).recommendations
        self.assertGreater(df["domain"].nunique(), 1)

    def test_filter_happens_before_similarity(self):
        """The TF-IDF index for a domain is fitted only on that domain's rows."""
        e = RecommendationEngine(real_projects())
        e.recommend(UserQuery(domain="Robotics", interests="x robot"), 3)
        idx = e._indexes["robotics"]
        self.assertEqual(len(idx.positions), 150)
        self.assertEqual(set(e.projects.iloc[idx.positions]["domain"]), {"Robotics"})
        self.assertEqual(idx.matrix.shape[0], 150)


class TfidfCosineTests(unittest.TestCase):
    def test_scores_equal_an_independent_cosine_computation(self):
        """Recompute cosine with plain numpy on the same TF-IDF vectors."""
        from sklearn.feature_extraction.text import TfidfVectorizer

        e = RecommendationEngine(real_projects())
        q = UserQuery(domain="Computer Vision", skill_level="Intermediate", interests="object detection, ocr",
                      skills="python, pytorch", available_time="16-30 Days", preferred_language="Python")
        res = e.recommend(q, 10, dedupe=False)
        resolution = e.resolver.resolve(q.domain)
        positions = np.flatnonzero(e._domain_keys == resolution.key)
        docs = [e._documents[i] for i in positions]
        vec = TfidfVectorizer(analyzer=analyze_text, sublinear_tf=True)
        matrix = vec.fit_transform(docs).toarray()
        qv = vec.transform([e.build_query_text(q, resolution)]).toarray()[0]
        manual = matrix @ qv / (np.linalg.norm(matrix, axis=1) * np.linalg.norm(qv))
        by_id = dict(zip(e.projects.iloc[positions]["project_id"], manual))
        for pid, score in zip(res.recommendations["project_id"], res.recommendations["match_score"]):
            self.assertAlmostEqual(score, by_id[pid], places=8, msg=pid)
        # and the engine really returned the global top-10 of that manual ranking
        expected_top = sorted(by_id.values(), reverse=True)[:10]
        np.testing.assert_allclose(sorted(res.recommendations["match_score"], reverse=True), expected_top, atol=1e-8)

    def test_scores_are_valid_sorted_and_deterministic(self):
        q = UserQuery(domain="Web Development", skill_level="Beginner", interests="dashboard, api", skills="javascript, sql")
        first = engine().recommend(q, 10).recommendations
        again = engine().recommend(q, 10).recommendations
        pd.testing.assert_frame_equal(first, again)
        scores = first["match_score"].tolist()
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(all(0.0 < s <= 1.0 for s in scores))

    def test_ties_break_by_project_id(self):
        df = make_projects(*[{"title": f"Same {i}", "description": "alpha beta"} for i in range(5)])
        df["project_id"] = ["T-005", "T-003", "T-001", "T-004", "T-002"]
        res = RecommendationEngine(df).recommend(UserQuery(interests="alpha"), 5, dedupe=False)
        self.assertEqual(ids(res), ["T-001", "T-002", "T-003", "T-004", "T-005"])

    def test_no_sklearn_or_pandas_warnings(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            e = RecommendationEngine(real_projects())
            e.recommend(UserQuery(domain="Any", interests="zzz"), 5)
            e.recommend(UserQuery(domain="DevOps", interests="docker"), 5)

    def test_interests_skills_level_language_and_description_all_influence_ranking(self):
        rows = [
            dict(title="A", description="housing price regression model", required_skills="pandas|sql", skill_level="Beginner", preferred_language="Python", interests="finance"),
            dict(title="B", description="image segmentation pipeline", required_skills="kubernetes", skill_level="Advanced", preferred_language="Go", interests="gaming"),
            dict(title="C", description="chatbot for support tickets", required_skills="nlp", skill_level="Intermediate", preferred_language="R", interests="education"),
        ]
        e = RecommendationEngine(make_projects(*rows))
        top = lambda **kw: e.recommend(UserQuery(domain="ML", **kw), 3).recommendations["title"].iloc[0]
        self.assertEqual(top(interests="regression housing"), "A")          # description
        self.assertEqual(top(skills="kubernetes"), "B")                      # skills
        self.assertEqual(top(interests="gaming"), "B")                       # interests
        self.assertEqual(top(skill_level="Intermediate", interests="ticket"), "C")  # level + text
        self.assertEqual(top(preferred_language="R", interests="support"), "C")     # language

    def test_multiple_skills_and_interests_rank_best_overlap_first(self):
        rows = [
            dict(title="one", required_skills="pandas", interests="finance"),
            dict(title="two", required_skills="pandas|sql", interests="finance|dashboards"),
            dict(title="three", required_skills="docker", interests="gaming"),
        ]
        res = RecommendationEngine(make_projects(*rows)).recommend(
            UserQuery(domain="Machine Learning", skills="pandas, sql, docker", interests="finance, dashboards"), 3)
        self.assertEqual(res.recommendations["title"].tolist()[:2], ["two", "one"])

    def test_multi_term_real_data_query_overlaps_top_results(self):
        q = UserQuery(domain="Data Science", skill_level="Beginner", interests="finance, dashboard", skills="python, pandas, plotly")
        df = engine().recommend(q, 10).recommendations
        self.assertEqual(set(df["domain"]), {"Data Science"})
        self.assertEqual(len(df), 10)
        blob = (df["interests"] + " " + df["required_libraries"] + " " + df["title"] + " " + df["description"]).str.lower()
        self.assertTrue(blob.str.contains("finance|dashboard|pandas|plotly").all())
        self.assertGreater(df["match_score"].iloc[0], df["match_score"].iloc[-1])


class TextNormalisationTests(unittest.TestCase):
    def test_language_names_survive_tokenisation(self):
        e = RecommendationEngine(make_projects(
            dict(title="r proj", preferred_language="R; Python"),
            dict(title="cpp proj", preferred_language="C++"),
            dict(title="go proj", preferred_language="Go"),
            dict(title="cs proj", preferred_language="C#"),
            dict(title="py proj", preferred_language="Python"),
        ))
        for lang, title in (("R", "r proj"), ("C++", "cpp proj"), ("Go", "go proj"), ("C#", "cs proj")):
            res = e.recommend(UserQuery(domain="ML", preferred_language=lang), 5).recommendations
            self.assertEqual(res["title"].iloc[0], title, lang)
        # Python is shared by "r proj" and "py proj" only: they must outrank the rest
        # (every in-domain project still shares the domain token, so none is excluded)
        res = e.recommend(UserQuery(domain="ML", preferred_language="Python"), 5).recommendations
        self.assertEqual(set(res["title"].iloc[:2]), {"r proj", "py proj"})

    def test_plural_folding(self):
        self.assertEqual(analyze_text("Dashboards")[0], analyze_text("dashboard")[0])
        self.assertEqual(analyze_text("libraries")[0], "library")
        self.assertIn("status", analyze_text("status"))
        self.assertIn("sql", analyze_text("SQL"))

    def test_bigrams_do_not_span_fields(self):
        tokens = analyze_text("tracker\nmachine learning")
        self.assertIn("machine learning", tokens)
        self.assertNotIn("tracker machine", tokens)

    def test_domain_vocabulary_not_eaten_by_stop_words(self):
        self.assertIn("system", analyze_text("Expert Systems system"))
        self.assertIn("full", analyze_text("Full Stack"))

    def test_levels(self):
        self.assertEqual(normalize_level("Senior"), "advanced")
        self.assertEqual(normalize_level("Beginner"), "beginner")
        self.assertEqual(normalize_level("Any"), "")
        self.assertEqual(normalize_level(None), "")


class TimeBudgetRankingTests(unittest.TestCase):
    def setUp(self):
        self.e = RecommendationEngine(make_projects(
            dict(title="quick", available_time="1-3 Days", description="alpha"),
            dict(title="medium", available_time="8-15 Days", description="alpha"),
            dict(title="long", available_time="1-3 Months", description="alpha"),
        ))

    def rank(self, **kw):
        return self.e.recommend(UserQuery(domain="ML", interests="alpha", **kw), 3, dedupe=False).recommendations["title"].tolist()

    def test_short_budget_prefers_short_projects(self):
        self.assertEqual(self.rank(available_time="1-3 Days")[0], "quick")

    def test_medium_budget_excludes_long_from_the_boost(self):
        order = self.rank(available_time="8-15 Days")
        self.assertEqual(order[-1], "long")
        self.assertEqual(set(order[:2]), {"quick", "medium"})

    def test_legacy_weeks_value_equals_the_days_bucket(self):
        self.assertEqual(self.rank(available_time="2-3 weeks"), self.rank(available_time="8-15 Days"))

    def test_explicit_budget_days_overrides_text(self):
        self.assertEqual(self.rank(time_budget_days=3)[0], "quick")

    def test_time_is_a_bounded_signal_not_dominant(self):
        e = RecommendationEngine(make_projects(
            dict(title="topic", available_time="1-3 Months", interests="astronomy"),
            dict(title="fast", available_time="1-3 Days", interests="cooking"),
        ))
        top = e.recommend(UserQuery(domain="ML", interests="astronomy", available_time="1-3 Days"), 2).recommendations
        self.assertEqual(top["title"].iloc[0], "topic")  # the stated interest beats pure time fit

    def test_unparseable_time_is_ignored(self):
        self.assertEqual(sorted(self.rank(available_time="whenever")), ["long", "medium", "quick"])


class DuplicateTests(unittest.TestCase):
    def test_title_variants_collapse_to_the_best_scoring_one(self):
        rows = [
            dict(title="Same Title", interests="music", description="x"),
            dict(title="Same Title", interests="sports", description="x"),
            dict(title="same title ", interests="finance", description="x"),   # case/space variant
            dict(title="Other", interests="finance", description="x"),
        ]
        res = RecommendationEngine(make_projects(*rows)).recommend(UserQuery(domain="ML", interests="sports"), 10)
        titles = res.recommendations["title"].str.strip().str.lower().tolist()
        self.assertEqual(len(titles), len(set(titles)))
        best = res.recommendations.iloc[0]
        self.assertEqual((best["title"], best["interests"]), ("Same Title", "sports"))

    def test_real_data_results_have_unique_titles_but_raw_ranking_does_not(self):
        q = UserQuery(domain="Machine Learning", skill_level="Beginner", interests="regression dashboard", preferred_language="Python")
        deduped = engine().recommend(q, 10).recommendations
        self.assertEqual(deduped["title"].nunique(), len(deduped))
        self.assertEqual(deduped["project_id"].nunique(), len(deduped))
        raw = engine().recommend(q, 10, dedupe=False).recommendations
        self.assertLess(raw["title"].nunique(), len(raw))  # the original defect: repeated titles

    def test_duplicate_ids_and_identical_rows_are_removed_at_load(self):
        df = make_projects(dict(title="A", description="x"), dict(title="B", description="y"))
        dup_id = df.iloc[[0]].copy()
        dup_id["title"] = "A again"
        clone = df.iloc[[1]].copy()
        clone["project_id"] = "T-999"
        e = RecommendationEngine(pd.concat([df, dup_id, clone], ignore_index=True))
        self.assertEqual(sorted(e.projects["project_id"]), ["T-001", "T-002"])


class MissingAndEmptyDataTests(unittest.TestCase):
    def test_empty_inputs_return_empty_not_arbitrary_rows(self):
        for q in (UserQuery(), UserQuery(domain="Any", skill_level="Any"), UserQuery(interests="zzzqqqxxx"), UserQuery(interests="the of and")):
            res = engine().recommend(q, 5)
            self.assertTrue(res.recommendations.empty, q)

    def test_chosen_domain_with_unmatched_interests_falls_back_to_domain_projects(self):
        res = engine().recommend(UserQuery(domain="AR/VR", interests="zzzqqqxxx"), 5)
        self.assertEqual(len(res.recommendations), 5)
        self.assertEqual(set(res.recommendations["domain"]), {"AR/VR"})
        self.assertTrue(engine().recommend(UserQuery(domain="Any", interests="zzzqqqxxx"), 5).recommendations.empty)

    def test_domain_only_still_works(self):
        df = engine().recommend(UserQuery(domain="Robotics"), 5).recommendations
        self.assertEqual(len(df), 5)
        self.assertEqual(set(df["domain"]), {"Robotics"})

    def test_empty_result_keeps_the_column_schema(self):
        df = engine().recommend(UserQuery(domain="Nope"), 5).recommendations
        self.assertIn("match_score", df.columns)
        self.assertIn("project_id", df.columns)
        self.assertEqual(len(df), 0)

    def test_empty_and_columnless_datasets(self):
        for frame in (None, pd.DataFrame(), make_projects().iloc[0:0] if False else pd.DataFrame(columns=["project_id", "title", "domain"])):
            e = RecommendationEngine(frame)
            self.assertTrue(e.recommend(UserQuery(domain="ML", interests="x"), 5).recommendations.empty)
            self.assertTrue(e.recommend(UserQuery(), 5).recommendations.empty)

    def test_missing_essential_column_is_a_clear_error(self):
        with self.assertRaises(ValueError) as ctx:
            RecommendationEngine(pd.DataFrame({"title": ["x"], "project_id": ["1"]}))
        self.assertIn("domain", str(ctx.exception))

    def test_missing_optional_columns_and_nan_cells_are_safe(self):
        df = pd.DataFrame({"project_id": ["1", "2", "3"], "title": ["A", "B", None],
                           "domain": ["Machine Learning", "Machine Learning", "Machine Learning"],
                           "description": ["regression model", np.nan, "x"]})
        e = RecommendationEngine(df)  # no skill_level/interests/... columns at all
        self.assertEqual(len(e.projects), 2)  # untitled row dropped
        res = e.recommend(UserQuery(domain="ml", interests="regression"), 5).recommendations
        self.assertEqual(res["title"].iloc[0], "A")  # B (NaN description) is still eligible, ranked lower
        self.assertNotIn("nan", " ".join(e._documents).lower().split())

    def test_all_blank_documents_do_not_crash(self):
        df = pd.DataFrame({"project_id": ["1"], "title": ["the"], "domain": ["of"]})
        res = RecommendationEngine(df).recommend(UserQuery(interests="the"), 5)
        self.assertTrue(res.recommendations.empty)

    def test_top_n_edge_values(self):
        q = UserQuery(domain="Cloud Computing", interests="deployment")
        self.assertEqual(len(engine().recommend(q, 0).recommendations), 0)
        self.assertEqual(len(engine().recommend(q, -3).recommendations), 0)
        self.assertEqual(len(engine().recommend(q, "3").recommendations), 3)
        self.assertEqual(len(engine().recommend(q, None).recommendations), 5)
        self.assertLessEqual(len(engine().recommend(q, 10_000).recommendations), 30)  # 30 unique titles/domain

    def test_fewer_eligible_than_requested(self):
        e = RecommendationEngine(make_projects(dict(title="only", description="alpha")))
        self.assertEqual(len(e.recommend(UserQuery(domain="ML", interests="alpha"), 10).recommendations), 1)

    def test_none_and_nan_query_fields(self):
        res = engine().recommend(UserQuery(domain=None, interests=float("nan"), skills=None), 5)
        self.assertTrue(res.recommendations.empty)


class LegacyApiTests(unittest.TestCase):
    """main.py (Streamlit) and old callers use these two functions unchanged."""

    def test_build_user_profile_is_a_str_with_the_old_content(self):
        p = build_user_profile("Machine Learning", "Beginner", "NLP dashboard", "8-15 Days", "Python")
        self.assertIsInstance(p, str)
        self.assertEqual(str(p), "machine learning beginner nlp dashboard 8-15 days python")
        self.assertEqual(p.query.domain, "Machine Learning")

    def test_recommend_projects_applies_the_domain_filter(self):
        p = build_user_profile("Machine Learning", "Beginner", "nlp text sentiment", "", "Python")
        df = recommend_projects(real_projects(), p, top_n=5)
        self.assertEqual(set(df["domain"]), {"Machine Learning"})
        self.assertIn("match_score", df.columns)
        self.assertEqual(df.index.tolist(), list(range(len(df))))  # main.py uses index + 1

    def test_plain_string_profile_still_works(self):
        df = recommend_projects(real_projects(), "regression dashboard", top_n=3)
        self.assertEqual(len(df), 3)

    def test_empty_profile_returns_empty_frame(self):
        self.assertTrue(recommend_projects(real_projects(), build_user_profile("", "", "", "", ""), 5).empty)

    def test_prebuilt_engine_is_reused(self):
        p = build_user_profile("Robotics", "", "", "", "")
        self.assertEqual(len(recommend_projects(None, p, 3, engine=engine())), 3)


if __name__ == "__main__":
    unittest.main()
