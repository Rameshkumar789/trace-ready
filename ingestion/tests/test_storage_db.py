import unittest

from traceready_backend.storage.db import InMemoryDraftStore, NonDurableStoreError


class StorageDbTest(unittest.TestCase):
    def test_in_memory_store_allows_local_test_usage(self):
        store = InMemoryDraftStore(environ={"TRACEREADY_ENV": "test"})

        store.insert_source({"id": "source-1"})

        self.assertEqual(store.sources, [{"id": "source-1"}])

    def test_in_memory_store_fails_in_production(self):
        with self.assertRaises(NonDurableStoreError):
            InMemoryDraftStore(environ={"TRACEREADY_ENV": "production"})


if __name__ == "__main__":
    unittest.main()
