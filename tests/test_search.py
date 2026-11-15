import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from src.search import search as search_module

ROWS = """id,question,category_code,duplicate_group,split
1,요금제 바꾸고 싶어요,PLAN_CHANGE,G01,test
2,다른 요금제로 변경할 수 있나요?,PLAN_CHANGE,G01,test
3,요금 납부일을 바꾸고 싶어요,PAYMENT_METHOD,G02,test
"""

VECTORS = {
    "요금제 바꾸고 싶어요": [1.0, 0.0],
    "다른 요금제로 변경할 수 있나요?": [0.8, 0.6],
    "요금 납부일을 바꾸고 싶어요": [0.0, 1.0],
    "요금제 변경": [1.0, 0.0],
}


def fake_encode(texts):
    return np.array([VECTORS[text] for text in texts])


class SearchTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / "questions.csv"
        path.write_text(ROWS, encoding="utf-8")

        self.index_path = Path(folder.name) / "index.npz"  # 기본은 실데이터 인덱스 없음

        search_module._load_index.cache_clear()
        self.addCleanup(search_module._load_index.cache_clear)
        for name, value in (("DATA_PATH", path), ("_encode", fake_encode),
                            ("INDEX_PATH", self.index_path)):
            patcher = mock.patch.object(search_module, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        env = mock.patch.dict("os.environ", {}, clear=False)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("QUESTION_TWIN_DATA", None)

    def fake_saved_index(self):
        self.index_path.write_bytes(b"")
        saved = mock.Mock(ids=[10, 11])
        saved.search.return_value = [{"id": 10}]
        patcher = mock.patch.object(search_module, "_load_saved_index", return_value=saved)
        patcher.start()
        self.addCleanup(patcher.stop)
        model = mock.patch.object(search_module, "_load_model", return_value="model")
        model.start()
        self.addCleanup(model.stop)
        return saved

    def test_sorted_by_score(self):
        results = search_module.search("요금제 변경")
        self.assertEqual([r["id"] for r in results], [1, 2, 3])
        self.assertEqual([r["score"] for r in results], [1.0, 0.8, 0.0])

    def test_result_keys(self):
        result = search_module.search("요금제 변경")[0]
        self.assertEqual(set(result), {"id", "question", "score", "category_code", "is_duplicate"})
        self.assertEqual(result["category_code"], "PLAN_CHANGE")

    def test_threshold(self):
        results = search_module.search("요금제 변경", threshold=0.9)
        self.assertEqual([r["is_duplicate"] for r in results], [True, False, False])

    def test_top_k(self):
        self.assertEqual(len(search_module.search("요금제 변경", top_k=2)), 2)

    def test_empty_query(self):
        self.assertEqual(search_module.search("   "), [])

    def test_too_long_query(self):
        with self.assertRaises(ValueError):
            search_module.search("가" * (search_module.MAX_QUERY_LENGTH + 1))

    def test_sample_when_no_saved_index(self):
        self.assertEqual(search_module.data_source(), "샘플 3건")

    def test_saved_index_used_when_present(self):
        saved = self.fake_saved_index()
        self.assertEqual(search_module.search(" 요금제 변경 ", top_k=2, threshold=0.5), [{"id": 10}])
        saved.search.assert_called_once_with("요금제 변경", top_k=2, threshold=0.5, encoder="model")
        self.assertEqual(search_module.data_source(), "실데이터 2건")

    def test_env_forces_sample(self):
        saved = self.fake_saved_index()
        os.environ["QUESTION_TWIN_DATA"] = "sample"
        self.assertEqual(search_module.search("요금제 변경")[0]["id"], 1)
        saved.search.assert_not_called()
        self.assertEqual(search_module.data_source(), "샘플 3건")


if __name__ == "__main__":
    unittest.main()