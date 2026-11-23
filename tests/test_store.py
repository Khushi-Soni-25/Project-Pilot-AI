import threading
import unittest

import pandas as pd

from tests.helpers import make_projects
from backend.store import ProjectStore


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class Loader:
    def __init__(self, frame=None, error=None):
        self.frame, self.error, self.calls = frame, error, 0

    def __call__(self):
        self.calls += 1
        if self.error:
            raise self.error
        return self.frame


JSON_FRAME = make_projects(dict(title="from json"))
MONGO_FRAME = make_projects(dict(title="from mongo"), dict(title="from mongo 2"))


class StoreTests(unittest.TestCase):
    def make(self, mongo, js=None, **kw):
        clock = Clock()
        store = ProjectStore(mongo, js or Loader(JSON_FRAME), ttl_seconds=60, mongo_retry_seconds=30, clock=clock, **kw)
        return store, clock

    def test_engine_is_cached_within_ttl(self):
        mongo, js = Loader(MONGO_FRAME), Loader(JSON_FRAME)
        store, clock = self.make(mongo, js)
        first = store.get_engine()
        clock.now += 59
        self.assertIs(store.get_engine(), first)
        self.assertEqual(mongo.calls, 1)

    def test_reloads_after_ttl(self):
        mongo = Loader(MONGO_FRAME)
        store, clock = self.make(mongo)
        first = store.get_engine()
        clock.now += 61
        self.assertIsNot(store.get_engine(), first)
        self.assertEqual(mongo.calls, 2)

    def test_mongo_preferred_when_it_has_data(self):
        store, _ = self.make(Loader(MONGO_FRAME))
        self.assertEqual(len(store.get_engine().projects), 2)
        self.assertEqual(store.source, "mongodb")

    def test_falls_back_to_json_when_mongo_is_down_and_backs_off(self):
        mongo, js = Loader(error=ConnectionError("down")), Loader(JSON_FRAME)
        store, clock = self.make(mongo, js)
        self.assertEqual(store.get_engine().projects["title"].tolist(), ["from json"])
        self.assertEqual(store.source, "json")
        clock.now += 61  # TTL passed, but still inside... no: back-off is 30s so mongo is retried
        store.get_engine()
        self.assertEqual(mongo.calls, 2)
        # force a reload inside the back-off window: mongo must NOT be contacted
        store.invalidate()
        store.get_engine()
        self.assertEqual(mongo.calls, 2)
        clock.now += 31
        store.invalidate()
        store.get_engine()
        self.assertEqual(mongo.calls, 3)

    def test_empty_mongo_falls_back_to_json(self):
        store, _ = self.make(Loader(pd.DataFrame()))
        self.assertEqual(store.get_engine().projects["title"].tolist(), ["from json"])

    def test_mongo_with_bad_schema_falls_back_to_json(self):
        store, _ = self.make(Loader(pd.DataFrame({"title": ["x"]})))
        self.assertEqual(store.source if store.get_engine() else "", "json")

    def test_serves_stale_data_if_reload_fails(self):
        mongo = Loader(MONGO_FRAME)
        js = Loader(JSON_FRAME)
        store, clock = self.make(mongo, js)
        first = store.get_engine()
        mongo.error, js.error = ConnectionError("x"), OSError("disk")
        clock.now += 61
        self.assertIs(store.get_engine(), first)

    def test_first_load_failure_propagates(self):
        store, _ = self.make(Loader(error=ConnectionError()), Loader(error=OSError("missing")))
        with self.assertRaises(OSError):
            store.get_engine()

    def test_thread_safe_single_build(self):
        mongo = Loader(MONGO_FRAME)
        store, _ = self.make(mongo)
        engines = []
        threads = [threading.Thread(target=lambda: engines.append(store.get_engine())) for _ in range(20)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(mongo.calls, 1)
        self.assertEqual(len({id(e) for e in engines}), 1)


if __name__ == "__main__":
    unittest.main()
