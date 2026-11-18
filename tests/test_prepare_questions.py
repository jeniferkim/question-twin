"""Synthetic-only tests for the new local #5 pipeline."""
import csv
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from src.data.prepare_questions import (
    PreparationError, _build_approved_rows, _private_key, detect_archive_kind,
    normalize_question, prepare, private_output_path,
)


def save_zip(path, rows):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("synthetic.json", json.dumps(rows, ensure_ascii=False))


def write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw = self.root / "data" / "raw" / "question_twin"
        self.raw.mkdir(parents=True)
        self.sources = self.root / "source.zip"
        self.labels = self.root / "labels.zip"
        self.codes = self.root / "codes.csv"
        self.review = self.raw / "review_candidates.csv"
        self.report = self.raw / "review_report.json"
        self.questions = self.raw / "questions.csv"
        self.approvals = self.raw / "approved_questions.csv"
        self.template = self.raw / "approval_template.csv"
        write_csv(self.codes, ["category_code", "aihub_category"],
                  [{"category_code": "PLAN_CHANGE", "aihub_category": "요금제 변경"}])
        save_zip(self.sources, [{"source": "synthetic", "source_id": "test-1",
                                 "consulting_category": "요금제 변경",
                                 "consulting_content": "상담사: 무엇을 도와드릴까요?\n고객: 요금제를 변경하고 싶어요."},
                                {"source": "synthetic", "source_id": "test-2",
                                 "consulting_category": "요금제 변경",
                                 "consulting_content": "고객: 더 저렴한 요금제로 바꾸고 싶어요."}])
        save_zip(self.labels, [{"source": "synthetic", "source_id": identifier,
                                "consulting_category": "요금제 변경",
                                "instructions": [{"tuning_type": "분류", "data": [{
                                    "task": "분류", "task_category": "상담 요건",
                                    "output": "단일 요건 민원"}]}]}
                               for identifier in ("test-1", "test-2")])

    def call_prepare(self, report=None, approvals=None):
        return prepare(sources_path=self.sources, labels_path=self.labels,
                       codes_path=self.codes, review_output=self.review,
                       report_output=report or self.report,
                       questions_output=self.questions, approvals_path=approvals,
                       approval_template=self.template, root=self.root)

    def test_review_first_without_fabricated_ground_truth(self):
        result = self.call_prepare()
        self.assertEqual(result["review_candidates"], 2)
        self.assertEqual(result["exported_rows"], 0)
        self.assertFalse(self.questions.exists())
        self.assertTrue(self.template.exists())
        raw = self.review.read_text("utf-8-sig")
        self.assertNotIn("test-1", raw)
        self.assertIn("needs_manual_review", raw)
        self.assertEqual(json.loads(self.report.read_text("utf-8"))["source_rows"], 2)
        self.assertEqual(self.call_prepare(), result)

    def test_approved_export_is_private_deterministic_and_not_overwritten(self):
        self.call_prepare()
        with self.review.open(encoding="utf-8-sig", newline="") as stream:
            reviews = list(csv.DictReader(stream))
        approvals = [{"source_key": item["source_key"],
                      "approved_question": item["question"]} for item in reviews]
        write_csv(self.approvals, ["source_key", "approved_question"], approvals)
        result = self.call_prepare(report=self.raw / "approved_report.json", approvals=self.approvals)
        self.assertTrue(result["exported"])
        self.assertEqual(result["exported_rows"], 2)
        with self.questions.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["category_code"] for row in rows}, {"PLAN_CHANGE"})
        self.assertEqual({row["duplicate_group"] for row in rows}, {""})
        self.assertEqual({row["split"] for row in rows}, {""})
        self.assertTrue(all(row["id"].isdigit() for row in rows))
        before = self.questions.read_bytes()
        self.call_prepare(report=self.raw / "approved_report.json", approvals=self.approvals)
        self.assertEqual(before, self.questions.read_bytes())
        write_csv(self.approvals, ["source_key", "approved_question"], [
            {"source_key": approvals[0]["source_key"], "approved_question": "다른 요금제로 변경하고 싶어요."}])
        with self.assertRaisesRegex(PreparationError, "output_exists_different"):
            self.call_prepare(report=self.raw / "approved_report.json", approvals=self.approvals)
        self.assertEqual(before, self.questions.read_bytes())

    def test_duplicate_questions_and_conflicts_are_not_silently_labeled(self):
        rows = [{"source_key": _private_key("one"), "category_code": "A"},
                {"source_key": _private_key("two"), "category_code": "A"}]
        approval = {row["source_key"]: "요금제 변경하고 싶어요" for row in rows}
        exported, stats = _build_approved_rows(rows, approval)
        self.assertEqual(len(exported), 1)
        self.assertEqual(stats["duplicate_texts_removed"], 1)
        rows[1]["category_code"] = "B"
        with self.assertRaisesRegex(PreparationError, "no_approved_questions"):
            _build_approved_rows(rows, approval)

    def test_private_paths_only(self):
        for target in (self.root / "data" / "questions.csv", self.root / "README.md",
                       self.root / "data" / "raw" / ".." / "untracked.csv"):
            with self.assertRaisesRegex(PreparationError, "output_must_be_under_data_raw"):
                private_output_path(target, self.root)
        self.assertEqual(detect_archive_kind(Path("source.zip.part0")), "zip")
        with self.assertRaises(PreparationError):
            detect_archive_kind(Path("source.tar.gz"))

    def test_privacy_check_blocks_unreviewed_patterns(self):
        rows = [{"source_key": _private_key("one"), "category_code": "A"}]
        with self.assertRaisesRegex(PreparationError, "approved_question_needs_privacy_review"):
            _build_approved_rows(rows, {rows[0]["source_key"]: "연락처 010-1234-5678 알려주세요"})

    def test_text_normalization_is_narrow(self):
        self.assertEqual(normalize_question("  요금제\n 변경   문의  "), "요금제 변경 문의")


if __name__ == "__main__":
    unittest.main()
