import unittest

from src.search.search import suggest_codes


def results(*codes):
    return [{"category_code": code} for code in codes]


class SuggestCodesTests(unittest.TestCase):
    def test_most_common_first(self):
        suggested = suggest_codes(results("BILL_INQUIRY", "PLAN_CHANGE", "PLAN_CHANGE"))
        self.assertEqual([s["code"] for s in suggested], ["PLAN_CHANGE", "BILL_INQUIRY"])
        self.assertEqual([s["count"] for s in suggested], [2, 1])

    def test_tie_prefers_higher_rank(self):
        suggested = suggest_codes(results("BILL_PAYMENT", "MICRO_PAYMENT", "MICRO_PAYMENT", "BILL_PAYMENT"))
        self.assertEqual([s["code"] for s in suggested], ["BILL_PAYMENT", "MICRO_PAYMENT"])

    def test_name_from_code_list(self):
        self.assertEqual(suggest_codes(results("PLAN_CHANGE"))[0]["name"], "요금제 변경")

    def test_unknown_code_uses_code_as_name(self):
        self.assertEqual(suggest_codes(results("UNKNOWN"))[0]["name"], "UNKNOWN")

    def test_empty_results(self):
        self.assertEqual(suggest_codes([]), [])


if __name__ == "__main__":
    unittest.main()