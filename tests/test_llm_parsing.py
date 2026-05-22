from __future__ import annotations

import pytest

from research_system.llm import (
    LLMConfigurationError,
    LLMResponseError,
    ask_llm,
    ask_llm_json,
    configure_llm_client,
    reset_llm_client,
)
from research_system.schemas import SchemaModel


class ExampleOutput(SchemaModel):
    title: str
    count: int


@pytest.fixture(autouse=True)
def clear_llm_client():
    reset_llm_client()
    yield
    reset_llm_client()


def test_ask_llm_requires_configured_client():
    with pytest.raises(LLMConfigurationError):
        ask_llm("hello")


def test_ask_llm_json_validates_model_from_json_response():
    configure_llm_client(lambda prompt: '{"title": "조사", "count": 3}')

    output = ask_llm_json("return json", ExampleOutput)

    assert output == ExampleOutput(title="조사", count=3)


def test_ask_llm_json_retries_after_bad_json():
    responses = iter(
        [
            "not json",
            '```json\n{"title": "재시도", "count": 2}\n```',
        ]
    )

    configure_llm_client(lambda prompt: next(responses))

    output = ask_llm_json("return json", ExampleOutput, max_attempts=2)

    assert output.count == 2


def test_ask_llm_json_retry_prompt_rejects_tool_argument_shape():
    prompts: list[str] = []
    responses = iter(
        [
            '{"query": "site:example.org evidence"}',
            '{"title": "최종", "count": 1}',
        ]
    )

    def client(prompt: str) -> str:
        prompts.append(prompt)
        return next(responses)

    configure_llm_client(client)

    output = ask_llm_json("return json", ExampleOutput, max_attempts=2)

    assert output.count == 1
    assert "standalone tool call" in prompts[1]
    assert '{"query": "..."}' in prompts[1]


def test_ask_llm_json_uses_structured_client_when_available():
    seen: dict[str, object] = {}

    class Client:
        def complete_structured(self, prompt: str, model_type: type[SchemaModel]) -> str:
            seen["prompt"] = prompt
            seen["model_type"] = model_type
            return '{"title": "구조화", "count": 4}'

        def complete(self, prompt: str) -> str:
            raise AssertionError("complete should not be used for structured output")

    configure_llm_client(Client())

    output = ask_llm_json("return json", ExampleOutput)

    assert output.count == 4
    assert seen == {"prompt": "return json", "model_type": ExampleOutput}


def test_ask_llm_json_reports_validation_fields():
    configure_llm_client(lambda prompt: '{"title": "조사"}')

    with pytest.raises(LLMResponseError) as exc_info:
        ask_llm_json("return json", ExampleOutput, max_attempts=1)

    assert "count" in str(exc_info.value)
    assert exc_info.value.validation_errors[0]["loc"] == ("count",)
