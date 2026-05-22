from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from research_system.context import AgentContext
from research_system.schemas import SchemaModel


class ToolExecutionError(RuntimeError):
    """Raised when a tool cannot complete its requested action."""


class Tool:
    name: str
    description: str

    def __init__(self, *, name: str, description: str) -> None:
        if not name.strip():
            raise ValueError("tool name must not be empty")
        if not description.strip():
            raise ValueError("tool description must not be empty")
        self.name = name
        self.description = description

    def run(self, **kwargs: Any) -> str:
        raise NotImplementedError

    def descriptor(self) -> dict[str, str]:
        return {"name": self.name, "description": self.description}


SearchBackend = Callable[[str, int], Sequence[Mapping[str, Any]]]
FetchBackend = Callable[..., str]


class WebSearchTool(Tool):
    def __init__(
        self,
        *,
        search: SearchBackend | None = None,
        name: str = "web_search",
        description: str = "Search the web and return source candidates.",
    ) -> None:
        super().__init__(name=name, description=description)
        self.search = search

    def run(self, **kwargs: Any) -> str:
        query = _require_text(kwargs, "query")
        limit = int(kwargs.get("limit", 5))
        if limit < 1:
            raise ToolExecutionError("limit must be at least 1")
        if self.search is None:
            raise ToolExecutionError(
                "No search backend configured for WebSearchTool."
            )

        results = list(self.search(query, limit))[:limit]
        payload = {
            "query": query,
            "results": [_to_jsonable(result) for result in results],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)


class FetchPageTool(Tool):
    def __init__(
        self,
        *,
        fetch: FetchBackend | None = None,
        timeout: float = 15.0,
        max_chars: int = 20_000,
        name: str = "fetch_page",
        description: str = "Fetch a web page body from an HTTP or HTTPS URL.",
    ) -> None:
        super().__init__(name=name, description=description)
        self.fetch = fetch
        self.timeout = timeout
        self.max_chars = max_chars

    def run(self, **kwargs: Any) -> str:
        url = _require_text(kwargs, "url")
        timeout = float(kwargs.get("timeout", self.timeout))
        max_chars = int(kwargs.get("max_chars", self.max_chars))
        _validate_http_url(url)

        try:
            content = (
                self.fetch(url, timeout=timeout)
                if self.fetch is not None
                else _fetch_url(url, timeout=timeout)
            )
        except Exception as exc:  # pragma: no cover - exact backend errors vary.
            raise ToolExecutionError(f"Failed to fetch {url}: {exc}") from exc

        if not isinstance(content, str):
            raise ToolExecutionError("fetch backend returned a non-string response")
        if max_chars < 1:
            raise ToolExecutionError("max_chars must be at least 1")
        if len(content) > max_chars:
            return f"{content[:max_chars]}\n...[truncated]"
        return content


class SaveArtifactTool(Tool):
    def __init__(
        self,
        *,
        context: AgentContext | None = None,
        output_root: Path | str = Path("outputs"),
        run_id: str | None = None,
        name: str = "save_artifact",
        description: str = "Save intermediate research output to the run directory.",
    ) -> None:
        super().__init__(name=name, description=description)
        self.context = context
        self.output_root = Path(output_root)
        self.run_id = run_id

    def run(self, **kwargs: Any) -> str:
        artifact_name = _require_text(kwargs, "name")
        content = kwargs.get("content", "")
        filename = str(kwargs.get("filename") or _default_filename(artifact_name, content))
        context = kwargs.get("context") or self.context
        target_dir = self._target_dir(context=context, run_id=kwargs.get("run_id"))
        target = _safe_child_path(target_dir, filename)

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_serialize_content(content), encoding="utf-8")

        if isinstance(context, AgentContext):
            context.set_artifact(artifact_name, content)

        return str(target)

    def _target_dir(self, *, context: Any, run_id: Any) -> Path:
        if context is not None:
            if not isinstance(context, AgentContext):
                raise ToolExecutionError("context must be an AgentContext")
            return context.run_dir

        effective_run_id = run_id or self.run_id
        if effective_run_id:
            return self.output_root / str(effective_run_id)
        return self.output_root


def _fetch_url(url: str, *, timeout: float) -> str:
    request = Request(url, headers={"User-Agent": "research-system/0.1"})
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _validate_http_url(url: str) -> None:
    scheme = urlparse(url).scheme.lower()
    if scheme not in {"http", "https"}:
        raise ToolExecutionError("url must use http or https")


def _require_text(kwargs: Mapping[str, Any], key: str) -> str:
    value = kwargs.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ToolExecutionError(f"{key} must be a non-empty string")
    return value


def _default_filename(name: str, content: Any) -> str:
    suffix = ".txt" if isinstance(content, str) else ".json"
    path = Path(name)
    if path.suffix:
        return name
    return f"{name}{suffix}"


def _safe_child_path(root: Path, filename: str) -> Path:
    relative = Path(filename)
    if relative.is_absolute():
        raise ToolExecutionError("filename must be relative")

    root_resolved = root.resolve()
    target = (root / relative).resolve()
    try:
        target.relative_to(root_resolved)
    except ValueError as exc:
        raise ToolExecutionError("filename must stay within the output directory") from exc
    return target


def _serialize_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(_to_jsonable(content), ensure_ascii=False, indent=2)


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, SchemaModel):
        return value.model_dump(mode="json")
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {
            str(key): _to_jsonable(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [_to_jsonable(item) for item in value]
    return value
