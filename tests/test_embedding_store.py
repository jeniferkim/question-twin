"""Offline synthetic tests for the new local #6 embedding cache."""
import csv
import hashlib
from pathlib import Path
import tempfile
import unittest

import numpy as np

from src.embedding.store import (
    DIM, IndexErrorSafe, SavedIndex, _csv_rows, build_index, load_index,
)


class SyntheticEncoder:
    def encode(self, sentences, **_kwargs):
        rows = []
        for text in sentences:
            vector = np.zeros(DIM, dtype=np.float32)
            vector[int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:2], "big") % DIM] = 1.0
            rows.append(vector)
        return np.stack(rows)


class EmbeddingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "data" / "raw" / "question_twin" / "questions.csv"
        self.source.parent.mkdir(parents=True)
        self.output = self.root / "data" / "embeddings" / "question_twin" / "minilm_index.npz"
        self.encoder = SyntheticEncoder()
        with self.source.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["id", "question", "category_code", "duplicate_group", "split"])
            writer.writeheader()
            writer.writerows([
                {"id": 100, "question": "휴대폰 요금제를 변경하고 싶어요", "category_code": "PLAN_CHANGE"},
                {"id": 200, "question": "미납 요금은 어디서 납부하나요", "category_code": "BILL_PAYMENT"},
            ])

    def test_build_load_search_no_model_download(self):
        report = build_index(self.source, self.output, encoder=self.encoder, root=self.root)
        self.assertEqual(report["rows"], 2)
        index = load_index(self.output, csv_path=self.source)
        self.assertEqual(index.vectors.shape, (2, 384))
        found = index.search("휴대폰 요금제를 변경하고 싶어요", encoder=self.encoder)
        self.assertEqual([x["id"] for x in found], [100, 200])
        self.assertEqual(found[0]["category_code"], "PLAN_CHANGE")
        self.assertEqual(set(found[0]), {"id", "question", "score", "category_code", "is_duplicate"})
        self.assertTrue(found[0]["is_duplicate"])
        self.assertEqual(index.search("", encoder=self.encoder), [])
        with self.assertRaisesRegex(IndexErrorSafe, "index_exists_will_not_overwrite"):
            build_index(self.source, self.output, encoder=self.encoder, root=self.root)

    def test_source_change_rejected(self):
        build_index(self.source, self.output, encoder=self.encoder, root=self.root)
        self.source.write_bytes(self.source.read_bytes() + b"\n")
        with self.assertRaisesRegex(IndexErrorSafe, "source_csv_changed"):
            load_index(self.output, csv_path=self.source)

    def test_output_path_restricted(self):
        with self.assertRaisesRegex(IndexErrorSafe, "index_must_be_under_data_embeddings"):
            build_index(self.source, self.root / "data" / "public.npz", encoder=self.encoder, root=self.root)

    def test_invalid_csv_rows_and_ids(self):
        with self.assertRaisesRegex(IndexErrorSafe, "invalid_source_row"):
            _csv_rows(b"id,question,category_code\n1,hello,A\n1,world,B\n")
        with self.assertRaisesRegex(IndexErrorSafe, "invalid_source_csv"):
            _csv_rows(b"id,question,category_code\nnot-an-integer,hello,A\n")

    def test_invalid_encoder_shape_does_not_create_file(self):
        class BadEncoder:
            def encode(self, sentences, **_kwargs):
                return np.zeros((len(sentences), DIM - 1), dtype=np.float32)
        with self.assertRaisesRegex(IndexErrorSafe, "invalid_index_shape"):
            build_index(self.source, self.output, encoder=BadEncoder(), root=self.root)
        self.assertFalse(self.output.exists())

    def test_corrupt_index_detected(self):
        self.output.parent.mkdir(parents=True)
        self.output.write_bytes(b"invalid zip bytes")
        with self.assertRaises(IndexErrorSafe):
            load_index(self.output)


if __name__ == "__main__":
    unittest.main()
