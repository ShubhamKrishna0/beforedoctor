"""Deterministic red-flag evaluator for pathway-driven conversations.

Evaluates JSON logic rules against gathered fields to detect urgent or
emergency conditions.  Pure function — no LLM, no I/O.
"""

from __future__ import annotations

import logging
from typing import Any

from app.models.pathway_models import RedFlagResult, RedFlagRule

logger = logging.getLogger(__name__)

# Supported leaf-node operators
_OPERATORS: dict[str, Any] = {
    "eq": lambda field_val, rule_val: field_val == rule_val,
    "lt": lambda field_val, rule_val: field_val < rule_val,
    "gte": lambda field_val, rule_val: field_val >= rule_val,
    "in": lambda field_val, rule_val: field_val in rule_val,
}


def _evaluate_node(node: Any, gathered_fields: dict[str, Any]) -> bool:
    """Recursively evaluate a single logic_json node.

    A node is either:
    * A leaf:  ``{"field": "x", "op": "eq", "value": 42}``
    * A combinator: ``{"all": [<node>, ...]}`` or ``{"any": [<node>, ...]}``

    Returns ``False`` when a referenced field is missing from
    *gathered_fields* (the field hasn't been collected yet, so the
    condition can't be confirmed).
    """
    if not isinstance(node, dict):
        return False

    # --- combinator nodes ---
    if "all" in node:
        children = node["all"]
        if not isinstance(children, list):
            return False
        return all(_evaluate_node(child, gathered_fields) for child in children)

    if "any" in node:
        children = node["any"]
        if not isinstance(children, list):
            return False
        return any(_evaluate_node(child, gathered_fields) for child in children)

    # --- leaf node ---
    field = node.get("field")
    op = node.get("op")
    value = node.get("value")

    if field is None or op is None or value is None:
        return False

    if field not in gathered_fields:
        return False

    op_fn = _OPERATORS.get(op)
    if op_fn is None:
        return False

    try:
        return op_fn(gathered_fields[field], value)
    except (TypeError, ValueError):
        return False


def evaluate(
    gathered_fields: dict[str, Any],
    rules: list[RedFlagRule],
) -> list[RedFlagResult]:
    """Evaluate *rules* against *gathered_fields* and return triggered results.

    * Operators supported: ``eq``, ``lt``, ``gte``, ``in``
    * Combinators supported: ``all``, ``any`` (arbitrarily nested)
    * A missing field causes its condition to evaluate to ``False``.
    * Malformed ``logic_json`` is logged as a warning and the rule is skipped.
    """
    results: list[RedFlagResult] = []

    for rule in rules:
        try:
            logic = rule.logic_json
            if not isinstance(logic, dict):
                logger.warning(
                    "Skipping rule %s: logic_json is not a dict", rule.rule_code
                )
                continue

            if _evaluate_node(logic, gathered_fields):
                results.append(
                    RedFlagResult(
                        rule_code=rule.rule_code,
                        urgency_level=rule.urgency_level,
                        message=rule.message,
                    )
                )
        except Exception:
            logger.warning(
                "Skipping rule %s due to malformed logic_json",
                rule.rule_code,
                exc_info=True,
            )

    return results
