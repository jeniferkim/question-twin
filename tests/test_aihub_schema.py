import unittest
from src.data.aihub_loader import DataError
from src.data.aihub_schema import private_key, requirement_labels, source_records


def label(category="상담 요건", task="분류"):
    return {"source": "synthetic-provider", "source_id": "synthetic-1",
            "consulting_category": "요금제 변경", "instructions": [
                {"tuning_type": "분류", "data": [{"task": task,
                 "task_category": category, "output": "단일 요건 민원"}]}]}


class SchemaTests(unittest.TestCase):
    def test_provider_scoped_id(self):
        a = {"source": "provider-a", "source_id": "synthetic-1"}
        b = {"source": "provider-b", "source_id": "synthetic-1"}
        self.assertNotEqual(private_key(a), private_key(b))

    def test_missing_id_rejected(self):
        with self.assertRaisesRegex(DataError, "invalid_source_identifier"):
            private_key({"source": "synthetic"})

    def test_requirement_only(self):
        result = requirement_labels([label(), label(category="상담 결과")])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].requirement, "단일 요건 민원")

    def test_qa_cannot_be_requirement(self):
        with self.assertRaisesRegex(DataError, "unexpected_requirement_task"):
            requirement_labels([label(task="질의응답")])

    def test_source_adapter(self):
        row = {"source": "synthetic", "source_id": "synthetic-1",
               "consulting_category": "요금제 변경", "consulting_content": "고객: 요금제를 변경하고 싶어요."}
        self.assertEqual(source_records([row])[0].category, "요금제 변경")

    def test_invalid_nested_shape(self):
        row = label()
        row["instructions"] = [{}]
        with self.assertRaisesRegex(DataError, "invalid_instruction_group"):
            requirement_labels([row])


if __name__ == "__main__":
    unittest.main()
