from __future__ import annotations

from types import SimpleNamespace

import pytest

from research_system.cli import _load_llm_backend
from research_system.llm import LLMConfigurationError
from research_system.openai_backend import OpenAIResponsesClient


class FakeResponses:
    def __init__(self) -> None:
        self.last_request = None

    def create(self, **kwargs):
        self.last_request = kwargs
        return SimpleNamespace(output_text='{"ok": true}')


def test_openai_responses_client_uses_high_reasoning_and_json_mode():
    responses = FakeResponses()
    fake_client = SimpleNamespace(responses=responses)
    client = OpenAIResponsesClient(
        model="gpt-test",
        reasoning_effort="high",
        verbosity="high",
        max_output_tokens=123,
        client=fake_client,
    )

    assert client.complete("Return JSON.") == '{"ok": true}'
    assert responses.last_request == {
        "model": "gpt-test",
        "input": "Return JSON.",
        "reasoning": {"effort": "high"},
        "text": {
            "format": {"type": "json_object"},
            "verbosity": "high",
        },
        "max_output_tokens": 123,
    }


def test_openai_backend_reads_environment(monkeypatch):
    monkeypatch.setenv("RESEARCH_SYSTEM_OPENAI_MODEL", "gpt-env")
    monkeypatch.setenv("RESEARCH_SYSTEM_OPENAI_REASONING_EFFORT", "medium")
    monkeypatch.setenv("RESEARCH_SYSTEM_OPENAI_VERBOSITY", "low")
    monkeypatch.setenv("RESEARCH_SYSTEM_OPENAI_MAX_OUTPUT_TOKENS", "456")

    client = OpenAIResponsesClient(client=SimpleNamespace(responses=FakeResponses()))

    assert client.model == "gpt-env"
    assert client.reasoning_effort == "medium"
    assert client.verbosity == "low"
    assert client.max_output_tokens == 456


def test_openai_backend_rejects_bad_token_limit(monkeypatch):
    monkeypatch.setenv("RESEARCH_SYSTEM_OPENAI_MAX_OUTPUT_TOKENS", "many")

    with pytest.raises(LLMConfigurationError, match="must be an integer"):
        OpenAIResponsesClient(client=SimpleNamespace(responses=FakeResponses()))


def test_cli_openai_alias_loads_backend():
    assert isinstance(_load_llm_backend("openai"), OpenAIResponsesClient)
