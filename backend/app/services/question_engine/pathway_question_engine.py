"""Pathway-driven question engine that selects the next question based on gathered fields."""

from __future__ import annotations

import logging
from typing import Any

from app.models.pathway_models import QuestionResult, QuestionTemplate
from app.services.pathway_data.pathway_data_provider import PathwayDataProvider

logger = logging.getLogger(__name__)


class PathwayQuestionEngine:
    """Selects the next pathway question, skipping already-answered fields."""

    def next_question(
        self,
        pathway_code: str,
        gathered_fields: dict[str, Any],
        pathway_data: PathwayDataProvider,
    ) -> QuestionResult:
        """Return the next unanswered question or signal completion.

        Iterates question templates sorted by ``ask_order_hint``, skips any
        whose ``field_code`` already appears in *gathered_fields*, and returns
        the first remaining template.  When all required fields are filled **or**
        no more templates remain, ``is_complete`` is ``True``.
        """
        templates = pathway_data.get_question_templates(pathway_code)
        required_fields = pathway_data.get_required_fields(pathway_code)

        # Check if all required fields are already gathered.
        all_required_filled = all(
            rf.field_code in gathered_fields
            for rf in required_fields
            if rf.is_required
        )

        if all_required_filled:
            return QuestionResult(is_complete=True)

        # Find the first unanswered template (templates are pre-sorted by ask_order_hint).
        for template in templates:
            if template.field_code not in gathered_fields:
                question_text = self._select_variant(template, gathered_fields)
                return QuestionResult(
                    question_text=question_text,
                    field_code=template.field_code,
                    is_complete=False,
                )

        # No more templates but some required fields may still be missing.
        # Signal complete anyway — the engine has exhausted its questions.
        return QuestionResult(is_complete=True)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _select_variant(
        template: QuestionTemplate,
        gathered_fields: dict[str, Any],
    ) -> str:
        """Pick the best question variant, falling back to the default text."""
        if not template.variants:
            return template.question_text

        age_months = gathered_fields.get("age_months")

        if age_months is not None:
            for variant in template.variants:
                if variant.age_context and _age_matches(age_months, variant.age_context):
                    return variant.variant_text

        # No age-based match — return the default question text.
        return template.question_text


def _age_matches(age_months: Any, age_context: dict) -> bool:
    """Check whether *age_months* satisfies an ``age_context`` filter.

    Supported keys in *age_context*:
    - ``min_months`` (inclusive lower bound)
    - ``max_months`` (inclusive upper bound)
    """
    try:
        age = int(age_months)
    except (TypeError, ValueError):
        return False

    min_m = age_context.get("min_months")
    max_m = age_context.get("max_months")

    if min_m is not None and age < int(min_m):
        return False
    if max_m is not None and age > int(max_m):
        return False

    return True
