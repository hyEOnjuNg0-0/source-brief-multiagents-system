from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_system.context import AgentContext
from research_system.tools import (
    FetchPageTool,
    SaveArtifactTool,
    ToolExecutionError,
    WebSearchTool,
)


def test_web_search_tool_uses_configured_backend():
    tool = WebSearchTool(
        search=lambda query, limit: [
            {
                "title": "Result",
                "url": "https://example.org",
                "snippet": f"{query}:{limit}",
            }
        ]
    )

    payload = json.loads(tool.run(query="research system", limit=3))

    assert payload["query"] == "research system"
    assert payload["results"][0]["snippet"] == "research system:3"


def test_web_search_tool_requires_backend():
    tool = WebSearchTool()

    with pytest.raises(ToolExecutionError, match="No search backend"):
        tool.run(query="research system")


def test_fetch_page_tool_uses_configured_backend_and_truncates():
    tool = FetchPageTool(fetch=lambda url, timeout: "abcdef", max_chars=3)

    content = tool.run(url="https://example.org/page")

    assert content == "abc\n...[truncated]"


def test_save_artifact_tool_writes_to_context_run_dir(tmp_path: Path):
    context = AgentContext(
        run_id="run_001",
        user_question="조사 질문",
        output_root=tmp_path,
    )
    tool = SaveArtifactTool()

    saved_path = Path(
        tool.run(
            name="plan",
            content={"id": "plan_001"},
            context=context,
        )
    )

    assert saved_path == tmp_path / "run_001" / "plan.json"
    assert json.loads(saved_path.read_text(encoding="utf-8")) == {"id": "plan_001"}
    assert context.get_artifact("plan") == {"id": "plan_001"}


def test_save_artifact_tool_rejects_path_traversal(tmp_path: Path):
    tool = SaveArtifactTool(output_root=tmp_path, run_id="run_001")

    with pytest.raises(ToolExecutionError, match="within the output directory"):
        tool.run(name="bad", filename="..\\bad.txt", content="bad")
