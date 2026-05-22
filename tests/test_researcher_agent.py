from __future__ import annotations

from pathlib import Path

import pytest

from research_system.agents.researcher import (
    ResearcherAgent,
    create_default_researchers,
)
from research_system.context import AgentContext
from research_system.schemas import AgentRole, ResearchAssignment
from research_system.tools import Tool


class DummyTool(Tool):
    def __init__(self) -> None:
        super().__init__(name="dummy", description="Dummy tool for tests.")

    def run(self, **kwargs):
        return "ok"


def _researcher_payload(role: str) -> dict:
    return {
        "agent_role": role,
        "assignment_focus": "official sources",
        "sources": [
            {
                "id": "source_001",
                "title": "Official page",
                "url": "https://example.org/official",
                "publisher": "Example",
                "source_type": "official_doc",
            },
            {
                "id": "source_002",
                "title": "Annual report",
                "url": "https://example.org/report",
                "publisher": "Example",
                "source_type": "annual_report",
            },
        ],
        "notes": [
            {
                "id": "note_001",
                "researcher": "Researcher A",
                "section_id": "overview",
                "topic": "Overview",
                "summary": "Summary tied to sources.",
                "source_ids": ["source_001", "source_002"],
            }
        ],
    }


def test_researcher_agent_runs_with_tools_and_updates_context(tmp_path: Path):
    agent = ResearcherAgent(
        name="Researcher A",
        role=AgentRole.RESEARCHER_A,
        llm=lambda prompt, model: _researcher_payload("researcher_a"),
        tools=[DummyTool()],
    )
    context = AgentContext(
        run_id="run_001",
        user_question="question",
        output_root=tmp_path,
    )

    output = agent.research(
        assignment=ResearchAssignment(
            agent="Researcher A",
            focus="official sources",
            required_source_types=["official_doc"],
        ),
        context=context,
        followup_request="Add one more official source.",
        task_id="researcher_a_followup_001",
    )

    assert output.agent_role == "researcher_a"
    assert context.get_artifact("researcher_a") == output
    assert context.messages[0].message_type == "followup_response"


def test_researcher_agent_requires_two_sources():
    payload = _researcher_payload("researcher_a")
    payload["sources"] = payload["sources"][:1]
    payload["notes"][0]["source_ids"] = ["source_001"]
    agent = ResearcherAgent(
        name="Researcher A",
        role=AgentRole.RESEARCHER_A,
        llm=lambda prompt, model: payload,
    )

    with pytest.raises(ValueError, match="at least two sources"):
        agent.research()


def test_create_default_researchers_returns_a_b_c():
    researchers = create_default_researchers(
        llm=lambda prompt, model: _researcher_payload("researcher_a")
    )

    assert [researcher.name for researcher in researchers] == [
        "Researcher A",
        "Researcher B",
        "Researcher C",
    ]
    assert len({researcher.focus for researcher in researchers}) == 3
