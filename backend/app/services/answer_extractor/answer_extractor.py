"""LLM-based extractor that parses free-text answers into structured field values."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.models.pathway_models import RequiredField
from app.services.ai_service.openai_client import get_openai_client

logger = logging.getLogger(__name__)

# Maps data_type → JSON Schema type + description hint for the LLM.
_TYPE_SCHEMA: dict[str, dict[str, Any]] = {
    "integer": {"type": ["integer", "null"], "description": "An integer value, or null if not extractable."},
    "number": {"type": ["number", "null"], "description": "A numeric value (int or float), or null if not extractable."},
    "boolean": {"type": ["boolean", "null"], "description": "true or false, or null if not extractable."},
    "text": {"type": ["string", "null"], "description": "Free-text string, or null if not extractable."},
    "datetime": {"type": ["string", "null"], "description": "ISO-8601 datetime string, or null if not extractable."},
    "single_select": {"type": ["string", "null"], "description": "One selected option as a string, or null if not extractable."},
    "multi_select": {
        "type": ["array", "null"],
        "items": {"type": "string"},
        "description": "A list of selected options, or null if not extractable.",
    },
    "temperature": {"type": ["number", "null"], "description": "Temperature reading as a number (Fahrenheit), or null if not extractable."},
    "medication": {"type": ["string", "null"], "description": "Medication name/description as a string, or null if not extractable."},
    "file_upload": {"type": ["string", "null"], "description": "Always null — file uploads cannot be extracted from text."},
}


def _json_schema_for_field(field: RequiredField) -> dict[str, Any]:
    """Return a JSON Schema property definition for a single field."""
    base = _TYPE_SCHEMA.get(field.data_type, _TYPE_SCHEMA["text"]).copy()
    base["description"] = f"{field.field_label} ({field.data_type}). {base.get('description', '')}"
    return base


def _build_system_prompt(
    target_field: RequiredField,
    all_fields: list[RequiredField],
    gathered_fields: dict[str, Any],
) -> str:
    """Build a system prompt instructing the LLM to extract field values."""
    already = ", ".join(f"{k}={v!r}" for k, v in gathered_fields.items()) if gathered_fields else "none yet"

    extractable = [f for f in all_fields if f.field_code not in gathered_fields and f.data_type != "file_upload"]

    field_descriptions = []
    for f in extractable:
        marker = " (PRIMARY — this is the question we just asked)" if f.field_code == target_field.field_code else ""
        field_descriptions.append(f"  - {f.field_code}: {f.field_label} (type: {f.data_type}){marker}")

    return "\n".join([
        "You are a medical answer extraction assistant. A parent is answering questions about their child's symptoms.",
        "",
        "Your job is to extract structured field values from the parent's free-text response.",
        "",
        f"Fields already gathered: {already}",
        "",
        "Fields still needed (extract any you can identify in the response):",
        *field_descriptions,
        "",
        "Rules:",
        "1. The PRIMARY field is the one we just asked about — try hardest to extract it.",
        "2. If the user also mentions information for other fields, extract those too (bonus extraction).",
        "3. For each field, return the value in the correct data type or null if you cannot extract it.",
        "4. For boolean fields: interpret yes/yeah/yep/true as true, no/nope/nah/false as false.",
        "5. For temperature fields: return the numeric value in Fahrenheit. Convert from Celsius if needed.",
        "6. For single_select fields: return the best matching option as a string.",
        "7. For multi_select fields: return a list of matching options.",
        "8. For datetime fields: return an ISO-8601 string.",
        "9. For file_upload fields: always return null (cannot extract from text).",
        "10. Only include fields in the output where you have reasonable confidence in the extracted value.",
        "",
        "Respond with ONLY a JSON object mapping field_code to extracted value. "
        "Omit fields where you cannot extract a value.",
    ])


def _build_response_schema(
    target_field: RequiredField,
    all_fields: list[RequiredField],
    gathered_fields: dict[str, Any],
) -> dict[str, Any]:
    """Build a JSON Schema for the structured LLM response."""
    properties: dict[str, Any] = {}
    for f in all_fields:
        if f.field_code not in gathered_fields and f.data_type != "file_upload":
            properties[f.field_code] = _json_schema_for_field(f)

    # Always include the target field even if somehow already gathered.
    if target_field.field_code not in properties and target_field.data_type != "file_upload":
        properties[target_field.field_code] = _json_schema_for_field(target_field)

    return {
        "type": "object",
        "properties": properties,
        "required": [],
        "additionalProperties": False,
    }


def _validate_value(value: Any, data_type: str) -> Any | None:
    """Return *value* if it matches *data_type*, otherwise ``None``."""
    if value is None:
        return None

    try:
        if data_type == "integer":
            if isinstance(value, bool):
                return None
            return int(value)
        if data_type == "number" or data_type == "temperature":
            if isinstance(value, bool):
                return None
            return float(value)
        if data_type == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                low = value.strip().lower()
                if low in ("true", "yes", "yeah", "yep"):
                    return True
                if low in ("false", "no", "nope", "nah"):
                    return False
            return None
        if data_type == "text" or data_type == "medication" or data_type == "single_select" or data_type == "datetime":
            return str(value)
        if data_type == "multi_select":
            if isinstance(value, list):
                return [str(v) for v in value]
            return None
        if data_type == "file_upload":
            return None
    except (ValueError, TypeError):
        return None

    # Unknown data_type — accept as-is.
    return value


class AnswerExtractor:
    """LLM call that parses free-text into structured field values."""

    async def extract(
        self,
        user_text: str,
        target_field: RequiredField,
        all_pathway_fields: list[RequiredField],
        gathered_fields: dict[str, Any],
    ) -> dict[str, Any]:
        """Extract field values from *user_text*.

        Returns a dict mapping ``field_code`` → extracted value.
        Returns an empty dict when extraction fails entirely.
        """
        if not user_text or not user_text.strip():
            return {}

        # Build a lookup of field_code → data_type for validation.
        type_lookup: dict[str, str] = {f.field_code: f.data_type for f in all_pathway_fields}
        type_lookup.setdefault(target_field.field_code, target_field.data_type)

        system_prompt = _build_system_prompt(target_field, all_pathway_fields, gathered_fields)
        response_schema = _build_response_schema(target_field, all_pathway_fields, gathered_fields)

        try:
            client = get_openai_client()
            response = await client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                temperature=0.0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "extracted_fields",
                        "strict": True,
                        "schema": response_schema,
                    },
                },
            )

            raw_content = response.choices[0].message.content or ""
            parsed: dict[str, Any] = json.loads(raw_content)
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            logger.warning("AnswerExtractor: failed to parse LLM response: %s", exc)
            return {}
        except Exception:
            logger.exception("AnswerExtractor: LLM call failed")
            return {}

        # Validate and filter extracted values.
        result: dict[str, Any] = {}
        for field_code, value in parsed.items():
            data_type = type_lookup.get(field_code)
            if data_type is None:
                continue  # Unknown field — skip.
            validated = _validate_value(value, data_type)
            if validated is not None:
                result[field_code] = validated

        return result
