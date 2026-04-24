import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.memory.memory_layer import MedicalFact, MemoryLayer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_table_mock(data):
    """Return a mock whose .execute() returns an object with .data = data."""
    mock = MagicMock()
    mock.execute.return_value = MagicMock(data=data)
    for method in ("select", "eq", "in_", "insert", "update"):
        getattr(mock, method).return_value = mock
    return mock


def _build_client_mock(table_data: dict[str, list]):
    """Build a supabase client mock keyed by table name."""
    schema_mock = MagicMock()
    schema_mock.table.side_effect = lambda name: _make_table_mock(
        table_data.get(name, [])
    )
    client = MagicMock()
    client.schema.return_value = schema_mock
    return client


# ---------------------------------------------------------------------------
# get_active_facts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.services.memory.memory_layer.get_supabase_client")
async def test_get_active_facts_returns_active_only(mock_get_client):
    rows = [
        {
            "id": "fact-1",
            "fact_type": "allergy",
            "fact_value": "penicillin",
            "source_conversation_id": "conv-1",
            "is_active": True,
        },
    ]
    mock_get_client.return_value = _build_client_mock(
        {"user_medical_memory": rows}
    )

    layer = MemoryLayer()
    facts = await layer.get_active_facts("user-1")

    assert len(facts) == 1
    assert facts[0].fact_type == "allergy"
    assert facts[0].fact_value == "penicillin"
    assert facts[0].is_active is True


@pytest.mark.asyncio
@patch("app.services.memory.memory_layer.get_supabase_client")
async def test_get_active_facts_returns_empty_on_no_data(mock_get_client):
    mock_get_client.return_value = _build_client_mock(
        {"user_medical_memory": []}
    )

    layer = MemoryLayer()
    facts = await layer.get_active_facts("user-1")

    assert facts == []


@pytest.mark.asyncio
@patch("app.services.memory.memory_layer.get_supabase_client")
async def test_get_active_facts_returns_empty_on_error(mock_get_client):
    mock_get_client.side_effect = Exception("DB down")

    layer = MemoryLayer()
    facts = await layer.get_active_facts("user-1")

    assert facts == []


# ---------------------------------------------------------------------------
# extract_and_store_facts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.services.memory.memory_layer.get_supabase_client")
@patch("app.services.memory.memory_layer.get_openai_client")
async def test_extract_and_store_facts_persists_valid_facts(
    mock_openai, mock_supabase
):
    llm_response = MagicMock()
    llm_response.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps(
                    {
                        "facts": [
                            {
                                "fact_type": "chronic_condition",
                                "fact_value": "type 2 diabetes",
                            },
                            {
                                "fact_type": "medication",
                                "fact_value": "metformin 500mg",
                            },
                        ]
                    }
                )
            )
        )
    ]
    openai_client = AsyncMock()
    openai_client.chat.completions.create = AsyncMock(return_value=llm_response)
    mock_openai.return_value = openai_client

    mock_supabase.return_value = _build_client_mock({"user_medical_memory": []})

    layer = MemoryLayer()
    facts = await layer.extract_and_store_facts(
        "user-1", "conv-1", "I have type 2 diabetes and take metformin 500mg"
    )

    assert len(facts) == 2
    assert facts[0].fact_type == "chronic_condition"
    assert facts[0].fact_value == "type 2 diabetes"
    assert facts[1].fact_type == "medication"
    assert facts[1].fact_value == "metformin 500mg"
    assert all(f.is_active is True for f in facts)


@pytest.mark.asyncio
@patch("app.services.memory.memory_layer.get_supabase_client")
@patch("app.services.memory.memory_layer.get_openai_client")
async def test_extract_and_store_facts_filters_invalid_types(
    mock_openai, mock_supabase
):
    llm_response = MagicMock()
    llm_response.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps(
                    {
                        "facts": [
                            {"fact_type": "allergy", "fact_value": "peanuts"},
                            {"fact_type": "invalid_type", "fact_value": "something"},
                            {"fact_type": "medication", "fact_value": ""},
                        ]
                    }
                )
            )
        )
    ]
    openai_client = AsyncMock()
    openai_client.chat.completions.create = AsyncMock(return_value=llm_response)
    mock_openai.return_value = openai_client

    mock_supabase.return_value = _build_client_mock({"user_medical_memory": []})

    layer = MemoryLayer()
    facts = await layer.extract_and_store_facts("user-1", "conv-1", "I'm allergic to peanuts")

    assert len(facts) == 1
    assert facts[0].fact_type == "allergy"
    assert facts[0].fact_value == "peanuts"


@pytest.mark.asyncio
@patch("app.services.memory.memory_layer.get_supabase_client")
@patch("app.services.memory.memory_layer.get_openai_client")
async def test_extract_and_store_facts_returns_empty_on_no_facts(
    mock_openai, mock_supabase
):
    llm_response = MagicMock()
    llm_response.choices = [
        MagicMock(message=MagicMock(content=json.dumps({"facts": []})))
    ]
    openai_client = AsyncMock()
    openai_client.chat.completions.create = AsyncMock(return_value=llm_response)
    mock_openai.return_value = openai_client

    mock_supabase.return_value = _build_client_mock({"user_medical_memory": []})

    layer = MemoryLayer()
    facts = await layer.extract_and_store_facts("user-1", "conv-1", "Hello, how are you?")

    assert facts == []


@pytest.mark.asyncio
@patch("app.services.memory.memory_layer.get_supabase_client")
@patch("app.services.memory.memory_layer.get_openai_client")
async def test_extract_and_store_facts_returns_empty_on_llm_error(
    mock_openai, mock_supabase
):
    openai_client = AsyncMock()
    openai_client.chat.completions.create = AsyncMock(side_effect=Exception("LLM error"))
    mock_openai.return_value = openai_client

    layer = MemoryLayer()
    facts = await layer.extract_and_store_facts("user-1", "conv-1", "some text")

    assert facts == []


# ---------------------------------------------------------------------------
# deactivate_fact
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.services.memory.memory_layer.get_supabase_client")
async def test_deactivate_fact_calls_update(mock_get_client):
    table_mock = _make_table_mock([])
    schema_mock = MagicMock()
    schema_mock.table.return_value = table_mock
    client = MagicMock()
    client.schema.return_value = schema_mock
    mock_get_client.return_value = client

    layer = MemoryLayer()
    await layer.deactivate_fact("fact-1")

    table_mock.update.assert_called_once_with({"is_active": False})


@pytest.mark.asyncio
@patch("app.services.memory.memory_layer.get_supabase_client")
async def test_deactivate_fact_does_not_crash_on_error(mock_get_client):
    mock_get_client.side_effect = Exception("DB down")

    layer = MemoryLayer()
    # Should not raise
    await layer.deactivate_fact("fact-1")


# ---------------------------------------------------------------------------
# MedicalFact model
# ---------------------------------------------------------------------------


def test_medical_fact_model():
    fact = MedicalFact(
        id="f-1",
        fact_type="chronic_condition",
        fact_value="asthma",
        source_conversation_id="conv-1",
        is_active=True,
    )
    assert fact.id == "f-1"
    assert fact.fact_type == "chronic_condition"
    assert fact.fact_value == "asthma"
    assert fact.source_conversation_id == "conv-1"
    assert fact.is_active is True
