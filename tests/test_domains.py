import unittest
from collections import defaultdict

from tests.helpers import real_projects
from src.domains import DOMAIN_ALIASES, DomainResolver, compact_key, domain_key, is_any


class DomainKeyTests(unittest.TestCase):
    def test_normalisation(self):
        self.assertEqual(domain_key("Internet of Things (IoT)"), "internet of things iot")
        self.assertEqual(domain_key("UI/UX  Design"), "ui ux design")
        self.assertEqual(domain_key("  AR/VR "), "ar vr")
        self.assertEqual(domain_key("R&D"), "r and d")
        self.assertEqual(compact_key("Cyber Security"), "cybersecurity")

    def test_missing_values_are_empty(self):
        for value in (None, float("nan"), "", "   "):
            self.assertEqual(domain_key(value), "")

    def test_any_detection(self):
        for value in ("", "Any", " any ", "ALL", None, "None", "N/A", "All Domains"):
            self.assertTrue(is_any(value), value)
        self.assertFalse(is_any("Machine Learning"))


class ResolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.names = sorted(set(real_projects()["domain"]))
        cls.resolver = DomainResolver(real_projects()["domain"])

    def test_every_dataset_domain_resolves_to_itself(self):
        self.assertEqual(len(self.names), 22)
        for name in self.names:
            r = self.resolver.resolve(name)
            self.assertEqual((r.status, r.name), ("matched", name))

    def test_case_spacing_and_punctuation_insensitive(self):
        cases = {
            "machine learning": "Machine Learning",
            "  MACHINE   LEARNING ": "Machine Learning",
            "cyber security": "Cybersecurity",
            "Cyber-Security": "Cybersecurity",
            "internet of things": "Internet of Things (IoT)",
            "ui ux design": "UI/UX Design",
            "AR VR": "AR/VR",
            "bigdata": "Big Data",
            "dev ops": "DevOps",
        }
        for raw, expected in cases.items():
            self.assertEqual(self.resolver.resolve(raw).name, expected, raw)

    def test_controlled_aliases(self):
        cases = {
            "ML": "Machine Learning", "AI": "Artificial Intelligence", "DL": "Deep Learning",
            "NLP": "Natural Language Processing", "CV": "Computer Vision", "IoT": "Internet of Things (IoT)",
            "VR": "AR/VR", "UX": "UI/UX Design", "DB": "Database Systems", "web dev": "Web Development",
            "mobile": "Mobile App Development", "recsys": "Recommendation Systems",
            "infosec": "Cybersecurity", "gamedev": "Game Development",
        }
        for raw, expected in cases.items():
            r = self.resolver.resolve(raw)
            self.assertEqual((r.status, r.name), ("matched", expected), raw)

    def test_aliases_are_unambiguous_and_point_at_real_domains(self):
        owner = defaultdict(set)
        for canonical, aliases in DOMAIN_ALIASES.items():
            self.assertIn(canonical, self.names, f"alias target {canonical!r} not in dataset")
            for alias in aliases:
                owner[domain_key(alias)].add(canonical)
        clashes = {k: v for k, v in owner.items() if len(v) > 1}
        self.assertEqual(clashes, {})
        # an alias must never shadow a different real domain's own name
        real_keys = {domain_key(n): n for n in self.names}
        for key, targets in owner.items():
            if key in real_keys:
                self.assertEqual(targets, {real_keys[key]}, key)

    def test_any_values_mean_no_filter(self):
        for value in ("", "Any", "all", None):
            r = self.resolver.resolve(value)
            self.assertEqual(r.status, "any")
            self.assertFalse(r.is_filter)

    def test_unknown_is_never_fuzzy_matched(self):
        for value in ("Machin Learning", "Quantum Computing", "Learning", "Machine", "Data", "Vision",
                      "Deep", "Systems", "Design", "Development"):
            r = self.resolver.resolve(value)
            self.assertEqual(r.status, "unknown", value)
            self.assertIsNone(r.name)
            self.assertTrue(r.is_filter)  # callers must filter (-> no results), not ignore it

    def test_dataset_without_a_domain_ignores_its_aliases(self):
        resolver = DomainResolver(["Robotics"])
        self.assertEqual(resolver.resolve("ml").status, "unknown")
        self.assertEqual(resolver.resolve("robot").name, "Robotics")

    def test_spelling_variants_in_data_collapse_to_one_domain(self):
        resolver = DomainResolver(["Machine Learning"] * 3 + ["machine  learning", "MACHINE LEARNING"])
        self.assertEqual(resolver.domains, ["Machine Learning"])  # most common spelling wins
        self.assertEqual(resolver.resolve("ML").name, "Machine Learning")

    def test_empty_dataset(self):
        resolver = DomainResolver([])
        self.assertEqual(resolver.domains, [])
        self.assertEqual(resolver.resolve("ML").status, "unknown")
        self.assertEqual(resolver.resolve("").status, "any")


if __name__ == "__main__":
    unittest.main()
