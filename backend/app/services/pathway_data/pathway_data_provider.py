"""Service that loads pathway data from the medicaldiary schema in Supabase.

Instead of reading YAML config files, this provider queries the shared
Supabase database's ``medicaldiary`` schema directly — the same tables
that the MedicalDiary manager app populates:

- ``medicaldiary.pathways``
- ``medicaldiary.pathway_required_fields``
- ``medicaldiary.question_templates``
- ``medicaldiary.question_variants``
- ``medicaldiary.red_flag_rules``

Data is cached in memory after the first load.  Falls back to the YAML
config files under ``config/pathways/`` when the database is unreachable.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml

from app.database.supabase_client import get_supabase_client
from app.models.pathway_models import (
    PathwayConfig,
    QuestionTemplate,
    QuestionVariant,
    RedFlagRule,
    RequiredField,
)

logger = logging.getLogger(__name__)

_MEDICALDIARY_SCHEMA = "medicaldiary"

# Fallback: YAML config directory (used when DB is unreachable)
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_CONFIG_DIR = _PROJECT_ROOT / "config" / "pathways"


class PathwayDataProvider:
    """Loads pathway definitions from the ``medicaldiary`` DB schema, with
    YAML fallback.  Caches in memory after first successful load."""

    def __init__(self, config_dir: Path | None = None) -> None:
        self._config_dir = config_dir or _DEFAULT_CONFIG_DIR
        self._cache: dict[str, PathwayConfig] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_all(self) -> dict[str, PathwayConfig]:
        """Load (or return cached) all pathway configs."""
        if self._cache is not None:
            return self._cache

        # Try database first
        try:
            pathways = self._load_from_database()
            if pathways:
                self._cache = pathways
                logger.info(
                    "Loaded %d pathways from medicaldiary schema", len(pathways)
                )
                return pathways
        except Exception:
            logger.exception(
                "Failed to load pathways from medicaldiary schema, "
                "falling back to YAML configs"
            )

        # Fallback to YAML files
        pathways = self._load_from_yaml()
        self._cache = pathways
        if pathways:
            logger.info("Loaded %d pathways from YAML fallback", len(pathways))
        return pathways

    def get_pathway(self, pathway_code: str) -> PathwayConfig | None:
        """Return a single PathwayConfig or None if not found."""
        return self.load_all().get(pathway_code)

    def get_required_fields(self, pathway_code: str) -> list[RequiredField]:
        """Return required fields sorted by display_order, or empty list."""
        pathway = self.get_pathway(pathway_code)
        if pathway is None:
            return []
        return sorted(pathway.required_fields, key=lambda f: f.display_order)

    def get_question_templates(
        self, pathway_code: str
    ) -> list[QuestionTemplate]:
        """Return question templates sorted by ask_order_hint, or empty list."""
        pathway = self.get_pathway(pathway_code)
        if pathway is None:
            return []
        return sorted(
            pathway.question_templates, key=lambda t: t.ask_order_hint
        )

    def get_red_flag_rules(self, pathway_code: str) -> list[RedFlagRule]:
        """Return red-flag rules for the pathway, or empty list."""
        pathway = self.get_pathway(pathway_code)
        if pathway is None:
            return []
        return list(pathway.red_flag_rules)

    def get_all_pathway_codes(self) -> list[str]:
        """Return a sorted list of all loaded pathway codes."""
        return sorted(self.load_all().keys())

    def invalidate_cache(self) -> None:
        """Force a reload on the next access."""
        self._cache = None

    # ------------------------------------------------------------------
    # Database loader (primary)
    # ------------------------------------------------------------------

    def _load_from_database(self) -> dict[str, PathwayConfig]:
        """Query the ``medicaldiary`` schema for all pathway data."""
        client = get_supabase_client()
        schema = _MEDICALDIARY_SCHEMA

        # 1. Load active pathways
        pathways_resp = (
            client.schema(schema)
            .table("pathways")
            .select("*")
            .eq("is_active", True)
            .order("priority")
            .execute()
        )
        pathway_rows = pathways_resp.data or []
        if not pathway_rows:
            return {}

        pathway_codes = [r["pathway_code"] for r in pathway_rows]

        # 2. Load required fields for all pathways
        fields_resp = (
            client.schema(schema)
            .table("pathway_required_fields")
            .select("*")
            .in_("pathway_code", pathway_codes)
            .order("display_order")
            .execute()
        )
        fields_by_pathway: dict[str, list[dict]] = {}
        for row in fields_resp.data or []:
            code = row["pathway_code"]
            fields_by_pathway.setdefault(code, []).append(row)

        # 3. Load question templates for all pathways
        templates_resp = (
            client.schema(schema)
            .table("question_templates")
            .select("*")
            .in_("pathway_code", pathway_codes)
            .eq("is_active", True)
            .order("ask_order_hint")
            .execute()
        )
        templates_by_pathway: dict[str, list[dict]] = {}
        template_ids: list[str] = []
        for row in templates_resp.data or []:
            code = row["pathway_code"]
            templates_by_pathway.setdefault(code, []).append(row)
            template_ids.append(row["id"])

        # 4. Load question variants (if any templates exist)
        variants_by_template: dict[str, list[dict]] = {}
        if template_ids:
            variants_resp = (
                client.schema(schema)
                .table("question_variants")
                .select("*")
                .in_("question_template_id", template_ids)
                .eq("is_active", True)
                .execute()
            )
            for row in variants_resp.data or []:
                tid = row["question_template_id"]
                variants_by_template.setdefault(tid, []).append(row)

        # 5. Load red flag rules for all pathways
        rules_resp = (
            client.schema(schema)
            .table("red_flag_rules")
            .select("*")
            .in_("pathway_code", pathway_codes)
            .eq("is_active", True)
            .execute()
        )
        rules_by_pathway: dict[str, list[dict]] = {}
        for row in rules_resp.data or []:
            code = row["pathway_code"]
            rules_by_pathway.setdefault(code, []).append(row)

        # 6. Assemble PathwayConfig objects
        result: dict[str, PathwayConfig] = {}
        for pw_row in pathway_rows:
            code = pw_row["pathway_code"]

            required_fields = [
                RequiredField(
                    field_code=f["field_code"],
                    field_label=f["field_label"],
                    data_type=str(f["data_type"]),
                    is_required=f["is_required"],
                    priority_weight=f["priority_weight"],
                    ask_group=f.get("ask_group") or "",
                    red_flag_relevance=f["red_flag_relevance"],
                    display_order=f["display_order"],
                )
                for f in fields_by_pathway.get(code, [])
            ]

            question_templates = []
            for t in templates_by_pathway.get(code, []):
                variants = [
                    QuestionVariant(
                        variant_text=v["variant_text"],
                        tone=v.get("tone"),
                        age_context=v.get("age_context_json"),
                    )
                    for v in variants_by_template.get(t["id"], [])
                ]
                question_templates.append(
                    QuestionTemplate(
                        question_code=t["question_code"],
                        field_code=t["field_code"],
                        question_text=t["question_text_template"],
                        expected_answer_type=str(t["expected_answer_type"]),
                        ask_order_hint=t["ask_order_hint"],
                        group_key=t.get("group_key") or "",
                        variants=variants,
                    )
                )

            red_flag_rules = [
                RedFlagRule(
                    rule_code=r["rule_code"],
                    description=r["description"],
                    logic_json=_ensure_dict(r["logic_json"]),
                    urgency_level=str(r["urgency_level"]),
                    message=r["recommended_message_template"],
                )
                for r in rules_by_pathway.get(code, [])
            ]

            result[code] = PathwayConfig(
                pathway_code=code,
                pathway_name=pw_row["pathway_name"],
                description=pw_row.get("description") or "",
                priority=pw_row["priority"],
                required_fields=required_fields,
                question_templates=question_templates,
                red_flag_rules=red_flag_rules,
            )

        return result

    # ------------------------------------------------------------------
    # YAML fallback loader
    # ------------------------------------------------------------------

    def _load_from_yaml(self) -> dict[str, PathwayConfig]:
        """Load pathway configs from YAML files (fallback)."""
        pathways: dict[str, PathwayConfig] = {}
        config_dir = self._config_dir

        if not config_dir.is_dir():
            logger.warning(
                "Pathway YAML config directory not found: %s", config_dir
            )
            return pathways

        for yaml_path in sorted(config_dir.glob("*.yaml")):
            try:
                raw = yaml_path.read_text(encoding="utf-8")
                data = yaml.safe_load(raw)
                if not isinstance(data, dict):
                    logger.error(
                        "Malformed YAML (not a mapping) in %s", yaml_path.name
                    )
                    continue
                config = PathwayConfig(**data)
                pathways[config.pathway_code] = config
            except Exception:
                logger.exception(
                    "Failed to load pathway file %s", yaml_path.name
                )

        return pathways


def _ensure_dict(value: Any) -> dict:
    """Ensure a value is a dict — handles JSON strings from Supabase."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    return {}
