"""Unit tests for PathwayQuestionEngine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.models.pathway_models import (
    QuestionTemplate,
    QuestionVariant,
    RequiredField,
)
from app.services.pathway_data.pathway_data_provider import PathwayDataProvider
from app.services.question_engine.pathway_question_engine import PathwayQuestionEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rf(field_code: str, is_required: bool = True, display_order: int = 10) -> RequiredField:
    """Shorthand factory for RequiredField."""
    return RequiredField(
        field_code=field_code,
        field_label=field_code,
        data_type="text",
        is_required=is_required,
        priority_weight=50,
        ask_group="g",
        red_flag_relevance=False,
        display_order=display_order,
    )


def _qt(
    field_code: str,
    ask_order_hint: int = 10,
    question_text: str | None = None,
    variants: list[QuestionVariant] | None = None,
) -> QuestionTemplate:
    """Shorthand factory for QuestionTemplate."""
    return QuestionTemplate(
        question_code=f"ask_{field_code}",
        field_code=field_code,
        question_text=question_text or f"What is {field_code}?",
        expected_answer_type="text",
        ask_order_hint=ask_order_hint,
        group_key="g",
        variants=variants or [],
    )


def _build_provider(
    required_fields: list[RequiredField],
    question_templates: list[QuestionTemplate],
) -> PathwayDataProvider:
    """Build a PathwayDataProvider backed by an in-memory pathway config."""
    import yaml, tempfile, os

    pathway_code = "test_pathway"
    data = {
        "pathway_code": pathway_code,
        "pathway_name": "Test",
        "description": "test",
        "priority": 1,
        "required_fields": [rf.model_dump() for rf in required_fields],
        "question_templates": [qt.model_dump() for qt in question_templates],
        "red_flag_rules": [],
    }
    tmpdir = Path(tempfile.mkdtemp())
    yaml_path = tmpdir / f"{pathway_code}.yaml"
    yaml_path.write_text(yaml.dump(data), encoding="utf-8")
    return PathwayDataProvider(config_dir=tmpdir)


PATHWAY_CODE = "test_pathway"


# ---------------------------------------------------------------------------
# Tests: question ordering and skipping
# ---------------------------------------------------------------------------

class TestQuestionOrdering:
    def test_returns_first_unanswered_question(self):
        provider = _build_provider(
            required_fields=[_rf("a"), _rf("b")],
            question_templates=[_qt("a", 10), _qt("b", 20)],
        )
        engine = PathwayQuestionEngine()
        result = engine.next_question(PATHWAY_CODE, {}, provider)

        assert result.is_complete is False
        assert result.field_code == "a"
        assert result.question_text == "What is a?"

    def test_skips_already_gathered_field(self):
        provider = _build_provider(
            required_fields=[_rf("a"), _rf("b")],
            question_templates=[_qt("a", 10), _qt("b", 20)],
        )
        engine = PathwayQuestionEngine()
        result = engine.next_question(PATHWAY_CODE, {"a": "val"}, provider)

        assert result.is_complete is False
        assert result.field_code == "b"

    def test_respects_ask_order_hint(self):
        """Templates with lower ask_order_hint come first."""
        provider = _build_provider(
            required_fields=[_rf("x"), _rf("y"), _rf("z")],
            question_templates=[
                _qt("z", 30),
                _qt("x", 10),
                _qt("y", 20),
            ],
        )
        engine = PathwayQuestionEngine()
        r1 = engine.next_question(PATHWAY_CODE, {}, provider)
        assert r1.field_code == "x"

        r2 = engine.next_question(PATHWAY_CODE, {"x": 1}, provider)
        assert r2.field_code == "y"

        r3 = engine.next_question(PATHWAY_CODE, {"x": 1, "y": 2}, provider)
        assert r3.field_code == "z"


# ---------------------------------------------------------------------------
# Tests: completion detection
# ---------------------------------------------------------------------------

class TestCompletionDetection:
    def test_complete_when_all_required_fields_filled(self):
        provider = _build_provider(
            required_fields=[_rf("a", is_required=True), _rf("b", is_required=True)],
            question_templates=[_qt("a", 10), _qt("b", 20)],
        )
        engine = PathwayQuestionEngine()
        result = engine.next_question(PATHWAY_CODE, {"a": 1, "b": 2}, provider)

        assert result.is_complete is True
        assert result.question_text is None

    def test_complete_when_optional_fields_remain(self):
        """Optional fields don't block completion."""
        provider = _build_provider(
            required_fields=[
                _rf("req", is_required=True),
                _rf("opt", is_required=False),
            ],
            question_templates=[_qt("req", 10), _qt("opt", 20)],
        )
        engine = PathwayQuestionEngine()
        result = engine.next_question(PATHWAY_CODE, {"req": "done"}, provider)

        assert result.is_complete is True

    def test_complete_when_no_templates_remain(self):
        """If all templates are answered but a required field has no template, signal complete."""
        provider = _build_provider(
            required_fields=[_rf("a"), _rf("b")],
            question_templates=[_qt("a", 10)],  # no template for "b"
        )
        engine = PathwayQuestionEngine()
        result = engine.next_question(PATHWAY_CODE, {"a": 1}, provider)

        assert result.is_complete is True

    def test_not_complete_when_required_field_missing(self):
        provider = _build_provider(
            required_fields=[_rf("a"), _rf("b")],
            question_templates=[_qt("a", 10), _qt("b", 20)],
        )
        engine = PathwayQuestionEngine()
        result = engine.next_question(PATHWAY_CODE, {"a": 1}, provider)

        assert result.is_complete is False
        assert result.field_code == "b"


# ---------------------------------------------------------------------------
# Tests: variant selection based on age context
# ---------------------------------------------------------------------------

class TestVariantSelection:
    def test_selects_variant_matching_age(self):
        variants = [
            QuestionVariant(
                variant_text="How old is your baby?",
                age_context={"min_months": 0, "max_months": 12},
            ),
            QuestionVariant(
                variant_text="How old is your teenager?",
                age_context={"min_months": 144, "max_months": 216},
            ),
        ]
        provider = _build_provider(
            required_fields=[_rf("age_months"), _rf("temp")],
            question_templates=[
                _qt("age_months", 10),
                _qt("temp", 20, question_text="What is the temp?", variants=variants),
            ],
        )
        engine = PathwayQuestionEngine()
        result = engine.next_question(PATHWAY_CODE, {"age_months": 6}, provider)

        assert result.field_code == "temp"
        assert result.question_text == "How old is your baby?"

    def test_falls_back_to_default_when_no_variant_matches(self):
        variants = [
            QuestionVariant(
                variant_text="Baby variant",
                age_context={"min_months": 0, "max_months": 3},
            ),
        ]
        provider = _build_provider(
            required_fields=[_rf("age_months"), _rf("temp")],
            question_templates=[
                _qt("age_months", 10),
                _qt("temp", 20, question_text="Default temp question", variants=variants),
            ],
        )
        engine = PathwayQuestionEngine()
        # age_months=24 doesn't match the 0-3 variant
        result = engine.next_question(PATHWAY_CODE, {"age_months": 24}, provider)

        assert result.question_text == "Default temp question"

    def test_falls_back_when_age_months_not_gathered(self):
        variants = [
            QuestionVariant(
                variant_text="Baby variant",
                age_context={"min_months": 0, "max_months": 12},
            ),
        ]
        provider = _build_provider(
            required_fields=[_rf("temp")],
            question_templates=[
                _qt("temp", 10, question_text="Default temp", variants=variants),
            ],
        )
        engine = PathwayQuestionEngine()
        result = engine.next_question(PATHWAY_CODE, {}, provider)

        assert result.question_text == "Default temp"

    def test_no_variants_uses_default_text(self):
        provider = _build_provider(
            required_fields=[_rf("a")],
            question_templates=[_qt("a", 10, question_text="Plain question")],
        )
        engine = PathwayQuestionEngine()
        result = engine.next_question(PATHWAY_CODE, {}, provider)

        assert result.question_text == "Plain question"
