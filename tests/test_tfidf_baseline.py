import unittest

from eval.tfidf_baseline import TfidfSearcher


def row(id, question, code, group):
    return {"id": id, "question": question, "category_code": code,
            "duplicate_group": group, "split": "tune"}


ROWS = [
    row(1, "요금제 바꾸고 싶어요", "PLAN_CHANGE", "G01"),
    row(2, "다른 요금제로 변경할 수 있나요?", "PLAN_CHANGE", "G01"),
    row(3, "요금 납부일을 바꾸고 싶어요", "PAYMENT_METHOD", "G02"),
]


class TfidfSearchTests(unittest.TestCase):
    def setUp(self):
        self.searcher = TfidfSearcher(ROWS)

    def test_result_keys(self):
        result = self.searcher.search("요금제 바꾸고 싶어요")[0]
        self.assertEqual(set(result), {"id", "question", "score", "category_code", "is_duplicate"})

    def test_same_question_first(self):
        result = self.searcher.search("요금제 바꾸고 싶어요")[0]
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["score"], 1.0)
        self.assertTrue(result["is_duplicate"])

    def test_sorted_by_score(self):
        results = self.searcher.search("요금제 바꾸고 싶어요")
        self.assertEqual(len(results), 3)
        self.assertGreaterEqual(results[0]["score"], results[1]["score"])
        self.assertGreaterEqual(results[1]["score"], results[2]["score"])

    def test_top_k(self):
        self.assertEqual(len(self.searcher.search("요금제 바꾸고 싶어요", top_k=2)), 2)

    def test_empty_query(self):
        self.assertEqual(self.searcher.search("   "), [])


if __name__ == "__main__":
    unittest.main()
