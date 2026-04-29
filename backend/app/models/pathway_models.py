"""Pydantic data models for the pathway-driven questioning system."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class RequiredField(BaseModel):
    """A data point needed for a pathway's clinical assessment."""

    field_code: str
    field_label: str
    data_type: str  # integer, boolean, text, datetime, single_select, multi_select, temperature, medication, number, file_upload
    is_required: bool
    priority_weight: int
    ask_group: str
    red_flag_relevance: bool
    display_order: int


class QuestionVariant(BaseModel):
    """An alternative phrasing of a QuestionTemplate."""

    variant_text: str
    tone: str | None = None
    age_context: dict | None = None


class QuestionTemplate(BaseModel):
    """A pre-authored question linked to a specific pathway and field."""

    question_code: str
    field_code: str
    question_text: str
    expected_answer_type: str
    ask_order_hint: int
    group_key: str
    variants: list[QuestionVariant] = []


class RedFlagRule(BaseModel):
    """A pathway-specific rule with JSON logic conditions and urgency level."""

    rule_code: str
    description: str
    logic_json: dict
    urgency_level: str  # "urgent" | "emergency"
    message: str


class PathwayConfig(BaseModel):
    """Full configuration for a single medical pathway."""

    pathway_code: str
    pathway_name: str
    description: str
    priority: int
    required_fields: list[RequiredField]
    question_templates: list[QuestionTemplate]
    red_flag_rules: list[RedFlagRule]


class PathwayState(BaseModel):
    """Per-conversation pathway state persisted in the database."""

    conversation_id: str
    pathway_code: str | None = None
    gathered_fields: dict[str, Any] = {}
    current_question_code: str | None = None
    triggered_red_flags: list[dict] = []


class QuestionResult(BaseModel):
    """Return value from PathwayQuestionEngine.next_question()."""

    question_text: str | None = None
    field_code: str | None = None
    is_complete: bool


class RedFlagResult(BaseModel):
    """A triggered red-flag evaluation result."""

    rule_code: str
    urgency_level: str
    message: str
