from __future__ import annotations

import os
from typing import Any

from research_system.llm import LLMConfigurationError, LLMResponseError


DEFAULT_MODEL = "gpt-5.5"
DEFAULT_REASONING_EFFORT = "high"
DEFAULT_VERBOSITY = "high"


class OpenAIResponsesClient:
    """LLM backend that calls OpenAI's Responses API."""

    def __init__(
        self,
        *,
        model: str | None = None,
        reasoning_effort: str | None = None,
        verbosity: str | None = None,
        max_output_tokens: int | None = None,
        api_key: str | None = None,
        client: Any | None = None,
    ) -> None:
        self.model = model or os.environ.get(
            "RESEARCH_SYSTEM_OPENAI_MODEL",
            DEFAULT_MODEL,
        )
        self.reasoning_effort = reasoning_effort or os.environ.get(
            "RESEARCH_SYSTEM_OPENAI_REASONING_EFFORT",
            DEFAULT_REASONING_EFFORT,
        )
        self.verbosity = verbosity or os.environ.get(
            "RESEARCH_SYSTEM_OPENAI_VERBOSITY",
            DEFAULT_VERBOSITY,
        )
        self.max_output_tokens = max_output_tokens or _optional_int_env(
            "RESEARCH_SYSTEM_OPENAI_MAX_OUTPUT_TOKENS"
        )
        self.api_key = api_key
        self._client = client

    def complete(self, prompt: str) -> str:
        if not prompt.strip():
            raise ValueError("prompt must not be empty")

        response = self._openai_client().responses.create(**self._request(prompt))
        text = _response_text(response)
        if not text.strip():
            raise LLMResponseError("OpenAI response did not include output text.")
        return text

    def _openai_client(self) -> Any:
        if self._client is not None:
            return self._client

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMConfigurationError(
                "OpenAI backend requires the 'openai' package. "
                "Install project dependencies first."
            ) from exc

        kwargs: dict[str, Any] = {}
        if self.api_key:
            kwargs["api_key"] = self.api_key
        self._client = OpenAI(**kwargs)
        return self._client

    def _request(self, prompt: str) -> dict[str, Any]:
        request: dict[str, Any] = {
            "model": self.model,
            "input": prompt,
            "reasoning": {"effort": self.reasoning_effort},
            "text": {
                "format": {"type": "json_object"},
                "verbosity": self.verbosity,
            },
        }
        if self.max_output_tokens is not None:
            request["max_output_tokens"] = self.max_output_tokens
        return request


def create_default_client() -> OpenAIResponsesClient:
    return OpenAIResponsesClient()


def _response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        return output_text

    if isinstance(response, dict):
        output_text = response.get("output_text")
        if isinstance(output_text, str):
            return output_text
        output = response.get("output", [])
    else:
        output = getattr(response, "output", [])

    parts: list[str] = []
    for item in output or []:
        content = item.get("content", []) if isinstance(item, dict) else getattr(item, "content", [])
        for content_item in content or []:
            text = (
                content_item.get("text")
                if isinstance(content_item, dict)
                else getattr(content_item, "text", None)
            )
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts)


def _optional_int_env(name: str) -> int | None:
    raw_value = os.environ.get(name)
    if raw_value is None or not raw_value.strip():
        return None
    try:
        return int(raw_value)
    except ValueError as exc:
        raise LLMConfigurationError(f"{name} must be an integer") from exc
