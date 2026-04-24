import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.medical_context.medical_context_service import (
    MedicalContext,
    MedicalContextService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _make_table_mock(data):
    """Return a mock whose .execute() returns an object with .data = data."""
    mock = MagicMock()
    mock.execute.return_value = MagicMock(data=data)
    # Allow chaining: .select().eq().gte().order().in_().limit() etc.
    for method in ("select", "eq", "gte", "order", "in_", "limit"):
        getattr(mock, method).return_value = mock
    return mock


def _build_client_mock(conversations, messages, ai_responses, all_messages):
    """Build a supabase client mock that returns different data per table."""
    table_map = {
        "conversations": _make_table_mock(conversations),
        "messages": _make_table_mock(messages),
        "ai_responses": _make_table_mock(ai_responses),
    }
    # We need two separate calls to "messages" table (user messages + all messages for IDs).
    # Use side_effect to return different mocks on successive calls.
    messages_call_count = {"n": 0}
    messages_mock_user = _make_table_mock(messages)
    messages_mock_all = _make_table_mock(all_messages)

    def table_side_effect(name):
        if name == "messages":
            messages_call_count["n"] += 1
            if messages_call_count["n"] == 1:
                return messages_mock_user
            return messages_mock_all
        return table_map.get(name, _make_table_mock([]))

    schema_mock = MagicMock()
    schema_mock.table.side_effect = table_side_effect

    client = MagicMock()
    client.schema.return_value = schema_mock
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.services.medical_context.medical_context_service.get_supabase_client")
async def test_get_context_returns_symptoms_and_responses(mock_get_client):
    now = datetime.now(timezone.utc)
    conv_id = "conv-1"
    msg_id = "msg-1"

    client = _build_client_mock(
        conversations=[{"id": conv_id}],
        messages=[
            {"text": "I have a headache", "created_at": _iso(now - timedelta(days=1)), "conversation_id": conv_id},
        ],
        ai_responses=[
            {"id": "resp-1", "response_json": {"summary_of_symptoms": "Headache"}, "created_at": _iso(now - timedelta(days=1)), "message_id": msg_id},
        ],
        all_messages=[{"id": msg_id}],
    )
    mock_get_client.return_value = client

    service = MedicalContextService()
    ctx = await service.get_context("user-1")

    assert isinstance(ctx, MedicalContext)
    assert len(ctx.prior_symptoms) == 1
    assert ctx.prior_symptoms[0]["text"] == "I have a headache"
    assert len(ctx.prior_responses) == 1
    assert ctx.prior_responses[0]["response_json"]["summary_of_symptoms"] == "Headache"


@pytest.mark.asyncio
@patch("app.services.medical_context.medical_context_service.get_supabase_client")
async def test_get_context_empty_when_no_conversations(mock_get_client):
    client = _build_client_mock(
        conversations=[],
        messages=[],
        ai_responses=[],
        all_messages=[],
    )
    mock_get_client.return_value = client

    service = MedicalContextService()
    ctx = await service.get_context("user-1")

    assert ctx.prior_symptoms == []
    assert ctx.prior_responses == []
    assert ctx.symptom_frequencies == {}


@pytest.mark.asyncio
@patch("app.services.medical_context.medical_context_service.get_supabase_client")
async def test_get_context_caps_prior_responses_at_20(mock_get_client):
    now = datetime.now(timezone.utc)
    conv_id = "conv-1"

    # Create 25 AI responses
    ai_responses = [
        {"id": f"resp-{i}", "response_json": {}, "created_at": _iso(now - timedelta(hours=i)), "message_id": f"msg-{i}"}
        for i in range(25)
    ]
    all_messages = [{"id": f"msg-{i}"} for i in range(25)]

    client = _build_client_mock(
        conversations=[{"id": conv_id}],
        messages=[],
        ai_responses=ai_responses,
        all_messages=all_messages,
    )
    mock_get_client.return_value = client

    service = MedicalContextService()
    ctx = await service.get_context("user-1")

    assert len(ctx.prior_responses) <= 20


@pytest.mark.asyncio
@patch("app.services.medical_context.medical_context_service.get_supabase_client")
async def test_get_context_computes_symptom_frequencies(mock_get_client):
    now = datetime.now(timezone.utc)
    conv_id = "conv-1"

    messages = [
        {"text": "headache", "created_at": _iso(now - timedelta(days=1)), "conversation_id": conv_id},
        {"text": "headache", "created_at": _iso(now - timedelta(days=2)), "conversation_id": conv_id},
        {"text": "headache", "created_at": _iso(now - timedelta(days=3)), "conversation_id": conv_id},
        {"text": "fever", "created_at": _iso(now - timedelta(days=1)), "conversation_id": conv_id},
        # This one is older than 7 days, should not count
        {"text": "headache", "created_at": _iso(now - timedelta(days=10)), "conversation_id": conv_id},
    ]

    client = _build_client_mock(
        conversations=[{"id": conv_id}],
        messages=messages,
        ai_responses=[],
        all_messages=[],
    )
    mock_get_client.return_value = client

    service = MedicalContextService()
    ctx = await service.get_context("user-1")

    assert ctx.symptom_frequencies.get("headache") == 3
    assert ctx.symptom_frequencies.get("fever") == 1


@pytest.mark.asyncio
@patch("app.services.medical_context.medical_context_service.get_supabase_client")
async def test_get_context_returns_empty_on_timeout(mock_get_client):
    """Simulate a slow DB call that exceeds the 3-second timeout."""

    async def slow_fetch(*args, **kwargs):
        await asyncio.sleep(10)

    service = MedicalContextService()
    service.TIMEOUT_SECONDS = 0.1  # Use a short timeout for the test

    # Make the client raise on any call to simulate a hang
    client = MagicMock()
    schema_mock = MagicMock()

    async def hang(*a, **kw):
        await asyncio.sleep(10)

    # Override _fetch_context to be slow
    original_fetch = service._fetch_context

    async def slow_context(user_id):
        await asyncio.sleep(10)
        return await original_fetch(user_id)

    service._fetch_context = slow_context
    mock_get_client.return_value = client

    ctx = await service.get_context("user-1")

    assert ctx.prior_symptoms == []
    assert ctx.prior_responses == []
    assert ctx.symptom_frequencies == {}


def test_format_for_prompt_empty_context():
    ctx = MedicalContext()
    result = MedicalContextService.format_for_prompt(ctx)
    assert result == ""


def test_format_for_prompt_with_data():
    ctx = MedicalContext(
        prior_symptoms=[
            {"text": "headache", "created_at": "2024-01-15T10:00:00+00:00"},
        ],
        prior_responses=[
            {"response_json": {"summary_of_symptoms": "Headache reported"}, "created_at": "2024-01-15T10:05:00+00:00"},
        ],
        symptom_frequencies={"headache": 3},
    )
    result = MedicalContextService.format_for_prompt(ctx)

    assert "--- MEDICAL CONTEXT ---" in result
    assert "--- END MEDICAL CONTEXT ---" in result
    assert "[Prior Symptoms]" in result
    assert "headache" in result
    assert "[Prior AI Responses]" in result
    assert "Headache reported" in result
    assert "[Symptom Frequencies - Last 7 Days]" in result
    assert "headache: 3 time(s)" in result
