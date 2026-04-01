from __future__ import annotations

import unittest
from unittest.mock import patch

from app.db import init_vector_store


class InitVectorStoreTest(unittest.TestCase):
    def test_main_uses_legacy_vector_store_for_initial_build(self) -> None:
        calls: dict[str, object] = {}

        class FakeVectorStore:
            def __init__(self, *args, **kwargs) -> None:
                calls["kwargs"] = kwargs
                self.index_path = "./vector_store/faiss.index"
                self.chunk_metadata_path = "./vector_store/chunks.pkl"

            def build_index(self, chunks) -> None:
                calls["chunks"] = chunks

            def save(self) -> None:
                calls["saved"] = True

            def get_stats(self) -> dict[str, int]:
                return {
                    "num_vectors": 1,
                    "dimension": 1536,
                    "num_chunks": 1,
                }

        with patch.object(
            init_vector_store,
            "load_products_from_db",
            return_value=[{"sku": "SKU001", "name": "demo", "text": "demo text"}],
        ), patch.object(
            init_vector_store,
            "chunk_product_texts",
            return_value=["demo chunk"],
        ), patch.object(
            init_vector_store,
            "VectorStore",
            FakeVectorStore,
        ):
            init_vector_store.main()

        self.assertEqual(calls["kwargs"], {"use_incremental": False})
        self.assertEqual(calls["chunks"], ["demo chunk"])
        self.assertTrue(calls["saved"])


if __name__ == "__main__":
    unittest.main()
