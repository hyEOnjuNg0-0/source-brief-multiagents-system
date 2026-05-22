from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_system.orchestrator import ResearchOrchestrator
from research_system.schemas import (
    CriticOutput,
    PlannerOutput,
    ResearcherOutput,
    SynthesizerOutput,
    VerifierOutput,
)


def _planner_payload() -> dict[str, Any]:
    return {
        "plan": {
            "id": "plan_001",
            "user_question": "question",
            "research_scope": {
                "target": "Example Co",
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
                    "focus": "official sources",
                    "required_source_types": ["official_doc"],
                },
                {
                    "agent": "Researcher B",
                    "focus": "news context",
                    "required_source_types": ["news"],
                },
                {
                    "agent": "Researcher C",
                    "focus": "risks and criticism",
                    "required_source_types": ["critical_source"],
                },
            ],
        }
    }


def _researcher_payload(role: str, prefix: str) -> dict[str, Any]:
    return {
        "agent_role": role,
        "assignment_focus": f"{prefix} focus",
        "sources": [
            {
                "id": f"{prefix}_source_001",
                "title": f"{prefix} Source 1",
                "url": f"https://example.org/{prefix}/1",
                "publisher": "Example",
                "source_type": "official_doc",
            },
            {
                "id": f"{prefix}_source_002",
                "title": f"{prefix} Source 2",
                "url": f"https://example.org/{prefix}/2",
                "publisher": "Example",
                "source_type": "news",
            },
        ],
        "notes": [
            {
                "id": f"{prefix}_note_001",
                "researcher": f"Researcher {prefix[-1].upper()}",
                "section_id": "overview",
                "topic": "Overview",
                "summary": "Summary tied to sources.",
                "source_ids": [f"{prefix}_source_001", f"{prefix}_source_002"],
            }
        ],
    }


def _critic_payload() -> dict[str, Any]:
    return {
        "reviews": [
            {
                "id": "review_001",
                "target_note_id": "researcher_c_note_001",
                "issues": [
                    {
                        "type": "missing_context",
                        "severity": "medium",
                        "description": "Critical sources are thin.",
                    }
                ],
            }
        ],
        "source_balance_notes": ["Official sources need balancing."],
        "recommended_followups": [
            "Researcher C: add one more critical source."
        ],
    }


def _verifier_payload() -> dict[str, Any]:
    return {
        "fact_checks": [
            {
                "id": f"fact_{index:03d}",
                "item": f"Fact {index}",
                "value": f"Value {index}",
                "status": "confirmed",
                "rationale": "Checked against research sources.",
                "source_ids": ["researcher_a_source_001"],
            }
            for index in range(1, 6)
        ],
        "checked_source_ids": ["researcher_a_source_001"],
        "confirmed_items": ["Fact 1", "Fact 2", "Fact 3", "Fact 4", "Fact 5"],
    }


def _synthesizer_payload() -> dict[str, Any]:
    return {
        "briefing": {
            "id": "briefing_001",
            "title": "Example Briefing",
            "user_question": "question",
            "executive_summary": "Summary.",
            "sections": [
                {
                    "heading": "Overview",
                    "section_type": "overview",
                    "content": "Overview content.",
                    "source_ids": ["researcher_a_source_001"],
                }
            ],
            "key_points": ["Point one."],
            "care_points": ["Follow-up evidence was requested for critical context."],
            "source_list": ["researcher_a_source_001", "researcher_a_source_002"],
        },
        "sources": [
            {
                "id": "researcher_a_source_001",
                "title": "A Source 1",
                "url": "https://example.org/researcher_a/1",
                "publisher": "Example",
                "source_type": "official_doc",
            },
            {
                "id": "researcher_a_source_002",
                "title": "A Source 2",
                "url": "https://example.org/researcher_a/2",
                "publisher": "Example",
                "source_type": "news",
            },
        ],
        "fact_checks": _verifier_payload()["fact_checks"],
        "unresolved_cautions": [],
    }


def test_orchestrator_runs_full_flow_and_followups(tmp_path: Path):
    calls: list[str] = []

    def fake_llm(prompt: str, model: type):
        if model is PlannerOutput:
            return _planner_payload()
        if model is ResearcherOutput:
            if '"name": "Researcher A"' in prompt:
                calls.append("researcher_a")
                return _researcher_payload("researcher_a", "researcher_a")
            if '"name": "Researcher B"' in prompt:
                calls.append("researcher_b")
                return _researcher_payload("researcher_b", "researcher_b")
            calls.append(
                "researcher_c_followup"
                if '"followup_request": "Researcher C:' in prompt
                else "researcher_c"
            )
            return _researcher_payload("researcher_c", "researcher_c")
        if model is CriticOutput:
            return _critic_payload()
        if model is VerifierOutput:
            return _verifier_payload()
        if model is SynthesizerOutput:
            return _synthesizer_payload()
        raise AssertionError(f"unexpected model: {model}")

    orchestrator = ResearchOrchestrator(llm=fake_llm, output_root=tmp_path)

    result = orchestrator.run("question", run_id="run_001")

    assert result.briefing_path.exists()
    assert calls == [
        "researcher_a",
        "researcher_b",
        "researcher_c",
        "researcher_c_followup",
    ]
    assert len(result.research_outputs) == 4
    assert (tmp_path / "run_001" / "plan.json").exists()
    assert (tmp_path / "run_001" / "researcher_c_critic_followup_004.json").exists()
    messages = json.loads(
        (tmp_path / "run_001" / "messages.json").read_text(encoding="utf-8")
    )
    assert any(message["message_type"] == "followup_request" for message in messages)
    assert any(message["message_type"] == "followup_response" for message in messages)
