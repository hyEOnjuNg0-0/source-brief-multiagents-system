from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from research_system.agents.base import Agent
from research_system.context import AgentContext
from research_system.schemas import AgentRole, AgentTask, SchemaModel
from research_system.tools import Tool


class ExampleOutput(SchemaModel):
    title: str
    count: int


class DummyTool(Tool):
    def __init__(self) -> None:
        super().__init__(name="dummy_tool", description="A tool exposed to prompts.")

    def run(self, **kwargs):
        return "ok"


def _prompt_file(tmp_path: Path) -> Path:
    path = tmp_path / "prompt.md"
    path.write_text("Base role prompt.", encoding="utf-8")
    return path


def _task() -> AgentTask:
    return AgentTask(
        id="task_001",
        target_agent="ExampleAgent",
        description="Produce structured output.",
        payload={"topic": "source-based research"},
    )


def test_agent_run_builds_prompt_validates_output_and_updates_memory(tmp_path: Path):
    seen: dict[str, object] = {}

    def fake_llm(prompt: str, model: type[ExampleOutput]) -> dict:
        seen["prompt"] = prompt
        seen["model"] = model
        return {"title": "Validated", "count": 2}

    agent = Agent(
        name="ExampleAgent",
        role=AgentRole.PLANNER,
        prompt_path=_prompt_file(tmp_path),
        output_model=ExampleOutput,
        llm=fake_llm,
        tools=[DummyTool()],
    )
    context = AgentContext(
        run_id="run_001",
        user_question="question",
        output_root=tmp_path,
    )

    output = agent.run(_task(), context=context)

    assert output == ExampleOutput(title="Validated", count=2)
    assert seen["model"] is ExampleOutput
    assert "Base role prompt." in str(seen["prompt"])
    assert '"name": "ExampleAgent"' in str(seen["prompt"])
    assert '"topic": "source-based research"' in str(seen["prompt"])
    assert '"name": "dummy_tool"' in str(seen["prompt"])
    assert '"properties"' in str(seen["prompt"])
    assert '"count"' in str(seen["prompt"])
    assert agent.memory[0].content == "Completed task task_001"


def test_agent_run_rejects_output_that_does_not_match_contract(tmp_path: Path):
    agent = Agent(
        name="ExampleAgent",
        role=AgentRole.PLANNER,
        prompt_path=_prompt_file(tmp_path),
        output_model=ExampleOutput,
        llm=lambda prompt, model: {"title": "Missing count"},
    )

    with pytest.raises(ValidationError, match="count"):
        agent.run(_task())

    assert agent.memory == []
