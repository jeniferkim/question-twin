import json
from io import BytesIO
from dataclasses import asdict
import tarfile
import unittest
import zipfile

from src.data.aihub_loader import (
    DataError, Limits, SourceRecord, RequirementLabel,
    extract_candidates, first_request, read_archive,
)


def zipped(members):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in members:
            archive.writestr(name, value)
    buffer.seek(0)
    return buffer


def tarred(name, raw, kind=tarfile.REGTYPE):
    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        info = tarfile.TarInfo(name)
        info.type = kind
        if kind == tarfile.REGTYPE:
            info.size = len(raw)
            archive.addfile(info, BytesIO(raw))
        else:
            info.linkname = "elsewhere"
            archive.addfile(info)
    buffer.seek(0)
    return buffer


class ArchiveTests(unittest.TestCase):
    def test_zip_leading_slash_is_only_an_in_memory_name(self):
        self.assertEqual(read_archive(zipped([("/a.json", '[{"source_id":"synthetic-1"}]')]), "zip"),
                         [{"source_id": "synthetic-1"}])

    def test_tar_zip_json(self):
        archive = tarred("data.zip", zipped([("a.json", "[{}]")]).getvalue())
        self.assertEqual(read_archive(archive, "tar"), [{}])

    def test_tar_json(self):
        self.assertEqual(read_archive(tarred("a.json", b"[{}]"), "tar"), [{}])

    def test_complete_zip_part0(self):
        raw = zipped([("a.json", "[{}]")]).getvalue()
        self.assertEqual(read_archive(tarred("data.zip.part0", raw), "tar"), [{}])

    def test_incomplete_zip_part0_rejected(self):
        raw = zipped([("a.json", "[{}]")]).getvalue()
        with self.assertRaisesRegex(DataError, "invalid_archive"):
            read_archive(tarred("data.zip.part0", raw[:len(raw)//2]), "tar")

    def test_empty_record_list(self):
        self.assertEqual(read_archive(zipped([("a.json", "[]")]), "zip"), [])

    def test_malformed_json_and_error_redaction(self):
        with self.assertRaises(DataError) as raised:
            read_archive(zipped([("private-name.json", "private invalid content")]), "zip")
        self.assertEqual(str(raised.exception), "invalid_json")
        self.assertIsNone(raised.exception.__cause__)

    def test_invalid_record_shapes(self):
        for raw in ('{}', '[null]', '[1]', '["text"]'):
            with self.subTest(raw=raw), self.assertRaisesRegex(DataError, "expected_record_list"):
                read_archive(zipped([("a.json", raw)]), "zip")

    def test_duplicate_json_keys(self):
        with self.assertRaisesRegex(DataError, "duplicate_json_key"):
            read_archive(zipped([("a.json", '[{"id":1,"id":2}]')]), "zip")

    def test_non_finite_json(self):
        with self.assertRaisesRegex(DataError, "invalid_json_constant"):
            read_archive(zipped([("a.json", '[{"x":NaN}]')]), "zip")

    def test_corrupt_archive(self):
        for kind in ("zip", "tar"):
            with self.subTest(kind=kind), self.assertRaisesRegex(DataError, "invalid_archive"):
                read_archive(BytesIO(b"not an archive"), kind)

    def test_path_traversal_rejected(self):
        for name in ("../a.json", "x/../../a.json", "..\\a.json"):
            with self.subTest(name=name), self.assertRaisesRegex(DataError, "unsafe_member_name"):
                read_archive(zipped([(name, "[{}]")]), "zip")

    def test_unsupported_extension(self):
        with self.assertRaisesRegex(DataError, "unsupported_member_type"):
            read_archive(zipped([("a.txt", "[{}]")]), "zip")

    def test_tar_symbolic_and_hard_links_rejected(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
            with self.subTest(kind=kind), self.assertRaisesRegex(DataError, "unsupported_tar_member"):
                read_archive(tarred("a.json", b"", kind), "tar")

    def test_zip_symbolic_link_rejected(self):
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            info = zipfile.ZipInfo("a.json")
            info.create_system = 3
            info.external_attr = 0o120777 << 16
            archive.writestr(info, "target")
        buffer.seek(0)
        with self.assertRaisesRegex(DataError, "unsupported_zip_member"):
            read_archive(buffer, "zip")

    def test_member_size_limit(self):
        with self.assertRaisesRegex(DataError, "size_limit"):
            read_archive(zipped([("a.json", "[{}]")]), "zip", Limits(member_bytes=2))

    def test_total_size_limit_counts_nested_zip_and_json(self):
        raw = zipped([("a.json", "[{}]")]).getvalue()
        with self.assertRaisesRegex(DataError, "total_size_limit"):
            read_archive(tarred("a.zip", raw), "tar", Limits(total_bytes=len(raw) + 3))

    def test_compression_ratio_limit(self):
        with self.assertRaisesRegex(DataError, "compression_ratio_limit"):
            read_archive(zipped([("a.json", json.dumps([{"x": "a" * 5000}]))]), "zip", Limits(ratio=2))

    def test_member_count_limit(self):
        with self.assertRaisesRegex(DataError, "member_limit"):
            read_archive(zipped([("a.json", "[]"), ("b.json", "[]")]), "zip", Limits(members=1))

    def test_record_count_limit(self):
        with self.assertRaisesRegex(DataError, "record_limit"):
            read_archive(zipped([("a.json", "[{},{}]")]), "zip", Limits(records=1))


class RequestTests(unittest.TestCase):
    def test_greeting_then_request_and_agent_excluded(self):
        result = first_request("상담사: 어떤 요금제를 변경하고 싶으신가요?\n고객: 안녕하세요.\n고객: 네\n고객: 요금제를 변경하고 싶어요.")
        self.assertEqual(result.text, "요금제를 변경하고 싶어요.")

    def test_multiple_requests_are_held(self):
        result = first_request("고객: 요금제를 바꾸고 싶어요. 그리고 납부일도 궁금해요.")
        self.assertEqual(result.reason, "multiple_request_review")

    def test_ambiguous_earlier_turn_is_not_silently_skipped(self):
        result = first_request("고객: 그거요\n고객: 요금제를 변경하고 싶어요.")
        self.assertIsNone(result.text)

    def test_no_customer_request(self):
        for text in ("상담사: 요금제 변경을 원하시나요?", "고객: 네\n고객: 감사합니다"):
            with self.subTest(text=text):
                self.assertEqual(first_request(text).reason, "no_customer_request")

    def test_multiline_unknown_roles_need_format_review(self):
        for text in ("고객: 요금제를 변경하고 싶어요.\n이어서 말한 내용", "직원: 요금제를 변경하고 싶어요."):
            self.assertEqual(first_request(text).reason, "unrecognized_turn_format")

    def test_tags_and_sensitive_patterns_are_held(self):
        for text in ("요금제 <이름> 변경하고 싶어요", "요금 문의 010-1234-5678", "요금 문의 a@example.invalid"):
            self.assertEqual(first_request("고객: " + text).reason, "privacy_or_tag_review")


class JoinTests(unittest.TestCase):
    @staticmethod
    def source(identifier="synthetic-1", category="요금제 변경"):
        return SourceRecord(identifier, category, "고객: 요금제를 변경하고 싶어요.")

    @staticmethod
    def label(identifier="synthetic-1", category="요금제 변경", requirement="단일 요건 민원"):
        return RequirementLabel(identifier, category, requirement)

    def test_join_and_no_fabricated_ground_truth(self):
        batch = extract_candidates([self.source()], [self.label()], {"요금제 변경": "TEL_PLAN"})
        self.assertEqual(batch.counts["candidate"], 1)
        candidate = batch.candidates[0]
        self.assertEqual(candidate.status, "needs_manual_review")
        self.assertNotIn("duplicate_group", asdict(candidate))
        self.assertNotIn("split", asdict(candidate))
        self.assertNotIn("synthetic-1", repr(batch))
        self.assertNotIn("변경하고", repr(candidate))

    def test_missing_and_orphan_label(self):
        batch = extract_candidates([self.source()], [self.label("synthetic-other")], {})
        self.assertEqual(batch.counts["missing_label"], 1)
        self.assertEqual(batch.counts["orphan_label_ids"], 1)
        self.assertEqual(batch.candidates, [])

    def test_duplicate_source_quarantined(self):
        batch = extract_candidates([self.source(), self.source()], [self.label()], {"요금제 변경": "TEL_PLAN"})
        self.assertEqual(batch.counts["duplicate_source_ids"], 1)
        self.assertFalse(batch.candidates)

    def test_duplicate_labels_quarantined(self):
        batch = extract_candidates([self.source()], [self.label(), self.label()], {"요금제 변경": "TEL_PLAN"})
        self.assertEqual(batch.counts["conflicting_label"], 1)
        self.assertFalse(batch.candidates)

    def test_category_mismatch(self):
        batch = extract_candidates([self.source()], [self.label(category="요금 납부")], {})
        self.assertEqual(batch.counts["category_mismatch"], 1)

    def test_no_automatic_whitespace_mapping(self):
        batch = extract_candidates([self.source(category="요금제변경")],
                                   [self.label(category="요금제변경")], {"요금제 변경": "TEL_PLAN"})
        self.assertEqual(batch.counts["unmapped_category"], 1)

    def test_multi_requirement_excluded(self):
        batch = extract_candidates([self.source()], [self.label(requirement="다수 요건 민원")], {})
        self.assertEqual(batch.counts["non_single_requirement"], 1)

    def test_reexecution_and_ordering(self):
        sources = [self.source("synthetic-2"), self.source("synthetic-1")]
        labels = [self.label("synthetic-1"), self.label("synthetic-2")]
        first = extract_candidates(sources, labels, {"요금제 변경": "TEL_PLAN"})
        second = extract_candidates(reversed(sources), reversed(labels), {"요금제 변경": "TEL_PLAN"})
        self.assertEqual(first, second)
        self.assertEqual(first.counts["unique_source_ids"], first.counts["candidate"])


if __name__ == "__main__":
    unittest.main()
