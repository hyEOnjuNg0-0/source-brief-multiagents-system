from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_system.agents.critic import CriticAgent
from research_system.context import AgentContext


def _critic_payload() -> dict:
    return {
        "reviews": [
            {
                "id": "review_001",
                "target_note_id": "note_001",
                "issues": [
                    {
                        "type": "missing_context",
                        "severity": "medium",
                        "description": "Critical and regulatory sources are thin.",
                    }
                ],
                "suggested_checks": ["Check post-2024 regulatory sources."],
            }
        ],
        "global_issues": [],
        "source_balance_notes": ["Official sources dominate the evidence."],
        "missing_context": ["Recent regulatory criticism is missing."],
        "recommended_followups": [
            "Researcher C: add post-2024 regulatory and criticism sources."
        ],
    }


def test_critic_agent_records_followup_requests(tmp_path: Path):
    agent = CriticAgent(llm=lambda prompt, model: _critic_payload())
    context = AgentContext(
        run_id="run_001",
        user_question="question",
        output_root=tmp_path,
    )

    output = agent.critique(context=context)

    assert context.get_artifact("critic") == output
    assert context.messages[0].message_type == "followup_request"
    assert context.messages[0].to_agent == "Researcher C"

    saved = json.loads(
        (tmp_path / "run_001" / "messages.json").read_text(encoding="utf-8")
    )
    assert saved[0]["content"].startswith("Researcher C:")


def test_critic_agent_requires_at_least_one_caution():
    payload = _critic_payload()
    payload["reviews"][0]["issues"] = []
    payload["source_balance_notes"] = []
    payload["missing_context"] = []
    payload["recommended_followups"] = []
    agent = CriticAgent(llm=lambda prompt, model: payload)

    with pytest.raises(ValueError, match="at least one caution"):
        agent.critique()
