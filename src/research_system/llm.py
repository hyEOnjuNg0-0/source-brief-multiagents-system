from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError


ModelT = TypeVar("ModelT", bound=BaseModel)


class LLMClient(Protocol):
    def complete(self, prompt: str) -> str:
        ...


class StructuredLLMClient(Protocol):
    def complete_structured(self, prompt: str, model_type: type[BaseModel]) -> str:
        ...


class LLMError(RuntimeError):
    """Base error for LLM call and response handling."""


class LLMConfigurationError(LLMError):
    """Raised when no concrete LLM backend has been configured."""


class LLMResponseError(LLMError):
    """Raised when an LLM response cannot be parsed or validated."""

    def __init__(
        self,
        message: str,
        *,
        raw_response: str | None = None,
        validation_errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.raw_response = raw_response
        self.validation_errors = validation_errors or []


LLMBackend = LLMClient | Callable[[str], str]

_client: LLMBackend | None = None
_JSON_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


def configure_llm_client(client: LLMBackend) -> None:
    """Configure the single LLM backend used by this package."""

    global _client
    _client = client


def reset_llm_client() -> None:
    """Clear the configured backend, mostly for tests."""

    global _client
    _client = None


def ask_llm(
    prompt: str,
    *,
    output_model: type[BaseModel] | None = None,
) -> str:
    if not prompt.strip():
        raise ValueError("prompt must not be empty")
    if _client is None:
        raise LLMConfigurationError(
            "No LLM client configured. Call configure_llm_client(...) first."
        )

    complete_structured = getattr(_client, "complete_structured", None)
    complete = getattr(_client, "complete", None)
    if output_model is not None and callable(complete_structured):
        response = complete_structured(prompt, output_model)
    elif callable(complete):
        response = complete(prompt)
    elif callable(_client):
        response = _client(prompt)
    else:
        raise LLMConfigurationError("Configured LLM client is not callable.")

    if not isinstance(response, str):
        raise LLMResponseError("LLM client returned a non-string response.")
    return response


def ask_llm_json(
    prompt: str,
    model_type: type[ModelT],
    *,
    max_attempts: int = 2,
) -> ModelT:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    current_prompt = prompt
    failures: list[str] = []
    raw_response = ""

    for attempt in range(1, max_attempts + 1):
        raw_response = ask_llm(current_prompt, output_model=model_type)
        try:
            payload = _parse_json_response(raw_response)
            return model_type.model_validate(payload)
        except LLMResponseError as exc:
            failures.append(str(exc))
            if attempt == max_attempts:
                raise LLMResponseError(
                    _format_failure_message(model_type, failures),
                    raw_response=raw_response,
                    validation_errors=exc.validation_errors,
                ) from exc
        except ValidationError as exc:
            validation_errors = exc.errors()
            failures.append(_format_validation_errors(model_type, validation_errors))
            if attempt == max_attempts:
                raise LLMResponseError(
                    _format_failure_message(model_type, failures),
                    raw_response=raw_response,
                    validation_errors=validation_errors,
                ) from exc

        current_prompt = _retry_prompt(prompt, failures[-1])

    raise LLMResponseError(_format_failure_message(model_type, failures))


def structured_ask_llm(prompt: str, output_model: type[ModelT]) -> ModelT:
    return ask_llm_json(prompt, output_model)


def _parse_json_response(response: str) -> Any:
    text = response.strip()
    if not text:
        raise LLMResponseError("LLM response was empty.", raw_response=response)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    for match in _JSON_FENCE_PATTERN.finditer(text):
        fenced = match.group(1).strip()
        if fenced:
            try:
                return json.loads(fenced)
            except json.JSONDecodeError:
                continue

    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            payload, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        return payload

    raise LLMResponseError(
        "LLM response did not contain valid JSON.",
        raw_response=response,
    )


def _retry_prompt(original_prompt: str, failure: str) -> str:
    return "\n\n".join(
        [
            original_prompt,
            "The previous response failed JSON validation.",
            failure,
            (
                "Do not return a standalone tool call, search request, or "
                "helper object such as {\"query\": \"...\"}. Return one complete "
                "JSON object for the requested output model with all required "
                "fields."
            ),
        ]
    )


def _format_validation_errors(
    model_type: type[BaseModel],
    validation_errors: list[dict[str, Any]],
) -> str:
    details = json.dumps(validation_errors, ensure_ascii=False, default=str)
    return f"{model_type.__name__} validation failed: {details}"


def _format_failure_message(
    model_type: type[BaseModel],
    failures: list[str],
) -> str:
    details = " | ".join(failures)
    return f"Could not parse LLM response as {model_type.__name__}: {details}"
