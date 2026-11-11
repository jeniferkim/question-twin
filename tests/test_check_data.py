import unittest

from eval.check_data import check

CODES = {"PLAN_CHANGE", "PAYMENT_METHOD"}


def row(id, question, code, group, split):
    return {"id": id, "question": question, "category_code": code,
            "duplicate_group": group, "split": split}


def clean_rows():
    return [
        row("1", "요금제 바꾸고 싶어요", "PLAN_CHANGE", "G01", "test"),
        row("2", "다른 요금제로 변경할 수 있나요?", "PLAN_CHANGE", "G01", "test"),
        row("3", "요금 납부일을 바꾸고 싶어요", "PAYMENT_METHOD", "G02", "tune"),
        row("4", "요금 빠져나가는 날짜 변경할 수 있나요?", "PAYMENT_METHOD", "G02", "tune"),
    ]


class CheckDataTests(unittest.TestCase):
    def test_clean_data(self):
        errors, warnings = check(clean_rows(), CODES)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_group_split_across(self):
        rows = clean_rows()
        rows[1]["split"] = "tune"
        errors, _ = check(rows, CODES)
        self.assertIn("한 묶음이 tune과 test에 나뉨: G01", errors)

    def test_group_with_two_codes(self):
        rows = clean_rows()
        rows[1]["category_code"] = "PAYMENT_METHOD"
        errors, _ = check(rows, CODES)
        self.assertIn("한 묶음에 상담 코드가 여러 개: G01 ['PAYMENT_METHOD', 'PLAN_CHANGE']", errors)

    def test_unknown_code(self):
        rows = clean_rows()
        rows[0]["category_code"] = "ACCOUNT"
        errors, _ = check(rows, CODES)
        self.assertIn("목록에 없는 상담 코드: id 1 -> ACCOUNT", errors)

    def test_duplicate_id(self):
        rows = clean_rows()
        rows[3]["id"] = "3"
        errors, _ = check(rows, CODES)
        self.assertIn("id 중복: 3 (2번)", errors)


if __name__ == "__main__":
    unittest.main()
