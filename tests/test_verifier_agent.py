from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_system.agents.verifier import VerifierAgent
from research_system.context import AgentContext
from research_system.schemas import ResearcherOutput


def _researcher_output() -> ResearcherOutput:
    return ResearcherOutput(
        agent_role="researcher_a",
        assignment_focus="official sources",
        sources=[
            {
                "id": "source_001",
                "title": "Source 1",
                "url": "https://example.org/1",
                "publisher": "Example",
                "source_type": "official_doc",
            },
            {
                "id": "source_002",
                "title": "Source 2",
                "url": "https://example.org/2",
                "publisher": "Example",
                "source_type": "news",
            },
        ],
        notes=[
            {
                "id": "note_001",
                "researcher": "Researcher A",
                "section_id": "overview",
                "topic": "Overview",
                "summary": "Summary",
                "source_ids": ["source_001", "source_002"],
            }
        ],
    )


def _verifier_payload(status: str = "confirmed") -> dict:
    fact_checks = []
    for index in range(1, 6):
        effective_status = status if index == 1 else "confirmed"
        fact_checks.append(
            {
                "id": f"fact_{index:03d}",
                "item": f"Fact {index}",
                "value": f"Value {index}",
                "status": effective_status,
                "rationale": "Checked against official and news sources.",
                "source_ids": ["source_001", "source_002"],
            }
        )
    return {
        "fact_checks": fact_checks,
        "checked_source_ids": ["source_001", "source_002"],
        "confirmed_items": ["Fact 2", "Fact 3", "Fact 4", "Fact 5"],
        "needs_care_items": ["Fact 1"] if status == "needs_care" else [],
        "conflicting_items": ["Fact 1"] if status == "conflicting" else [],
    }


def test_verifier_agent_records_followups_for_weak_facts(tmp_path: Path):
    agent = VerifierAgent(llm=lambda prompt, model: _verifier_payload("needs_care"))
    context = AgentContext(
        run_id="run_001",
        user_question="question",
        output_root=tmp_path,
    )
    context.set_artifact("researcher_a", _researcher_output())

    output = agent.verify(context=context)

    assert context.get_artifact("verifier") == output
    assert context.messages[0].message_type == "followup_request"
    assert context.messages[0].to_agent == "Researcher A"

    saved = json.loads(
        (tmp_path / "run_001" / "messages.json").read_text(encoding="utf-8")
    )
    assert "Recheck fact" in saved[0]["content"]


def test_verifier_agent_requires_about_five_fact_checks():
    payload = _verifier_payload()
    payload["fact_checks"] = payload["fact_checks"][:4]
    agent = VerifierAgent(llm=lambda prompt, model: payload)

    with pytest.raises(ValueError, match="at least 5 fact checks"):
        agent.verify()


def test_verifier_agent_rejects_unknown_source_ids_in_context():
    payload = _verifier_payload()
    payload["fact_checks"][0]["source_ids"] = ["source_missing"]
    agent = VerifierAgent(llm=lambda prompt, model: payload)
    context = AgentContext(run_id="run_001", user_question="question")
    context.set_artifact("researcher_a", _researcher_output())

    with pytest.raises(ValueError, match="unknown source_ids"):
        agent.verify(context=context)
