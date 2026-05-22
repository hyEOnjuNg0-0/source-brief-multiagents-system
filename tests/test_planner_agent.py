from __future__ import annotations

from pathlib import Path

import pytest

from research_system.agents.planner import PlannerAgent
from research_system.context import AgentContext
from research_system.schemas import PlannerOutput


def _planner_payload() -> dict:
    return {
        "plan": {
            "id": "plan_001",
            "user_question": "맥도날드의 역사와 운영 원칙을 조사해줘",
            "research_scope": {
                "target": "McDonald's",
                "target_type": "company",
            },
            "briefing_sections": [
                {
                    "id": "overview",
                    "title": "Overview",
                    "section_type": "overview",
                    "priority": "high",
                }
            ],
            "source_requirements": ["official_doc", "news", "critical_source"],
            "research_assignments": [
                {
                    "agent": "Researcher A",
                    "focus": "official and primary sources",
                    "required_source_types": ["official_doc"],
                },
                {
                    "agent": "Researcher B",
                    "focus": "news and industry context",
                    "required_source_types": ["news"],
                },
                {
                    "agent": "Researcher C",
                    "focus": "risks and criticism",
                    "required_source_types": ["critical_source"],
                },
            ],
        },
        "assumptions": [],
        "missing_inputs": [],
        "handoff_notes": ["Researcher assignments are split by source type."],
    }


def test_planner_agent_creates_plan_and_updates_context(tmp_path: Path):
    agent = PlannerAgent(llm=lambda prompt, model: _planner_payload())
    context = AgentContext(
        run_id="run_001",
        user_question="맥도날드의 역사와 운영 원칙을 조사해줘",
        output_root=tmp_path,
    )

    output = agent.plan(context.user_question, context=context)

    assert isinstance(output, PlannerOutput)
    assert context.get_artifact("plan").id == "plan_001"
    assert context.messages[0].message_type == "handoff"
    assert (tmp_path / "run_001" / "messages.json").exists()


def test_planner_agent_rejects_missing_researcher_assignments():
    payload = _planner_payload()
    payload["plan"]["research_assignments"] = payload["plan"]["research_assignments"][:2]
    agent = PlannerAgent(llm=lambda prompt, model: payload)

    with pytest.raises(ValueError, match="Researcher C"):
        agent.plan("question")
