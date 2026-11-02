"""Provider adapter for the locally verified schema; no files or logs are written."""
import json

from .aihub_loader import DataError, RequirementLabel, SourceRecord


def private_key(row):
    # An ID may be scoped to one provider. Both components come from JSON.
    values = [row.get("source"), row.get("source_id")]
    if not all(isinstance(value, str) and value for value in values):
        raise DataError("invalid_source_identifier")
    return json.dumps(values, ensure_ascii=True, separators=(",", ":"))


def source_records(rows):
    result = []
    for row in rows:
        category, content = row.get("consulting_category"), row.get("consulting_content")
        if not isinstance(category, str) or not category or not isinstance(content, str):
            raise DataError("invalid_source_fields")
        result.append(SourceRecord(private_key(row), category, content))
    return result


def requirement_labels(rows):
    result = []
    for row in rows:
        key = private_key(row)
        category = row.get("consulting_category")
        instructions = row.get("instructions")
        if not isinstance(category, str) or not isinstance(instructions, list):
            raise DataError("invalid_label_fields")
        for group in instructions:
            if not isinstance(group, dict) or not isinstance(group.get("data"), list):
                raise DataError("invalid_instruction_group")
            for item in group["data"]:
                if not isinstance(item, dict):
                    raise DataError("invalid_instruction_record")
                if item.get("task_category") != "상담 요건":
                    continue
                if group.get("tuning_type") != "분류" or item.get("task") != "분류":
                    raise DataError("unexpected_requirement_task")
                output = item.get("output")
                if not isinstance(output, str):
                    raise DataError("invalid_requirement_output")
                result.append(RequirementLabel(key, category, output))
    return result
