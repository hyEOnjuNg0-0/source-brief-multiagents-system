from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from research_system.context import AgentContext
from research_system.orchestrator import ResearchOrchestrator
from research_system.quality import ResearchQualityError, validate_mvp_quality
from research_system.schemas import (
    CriticOutput,
    PlannerOutput,
    ResearchPlan,
    ResearcherOutput,
    SynthesizerOutput,
    VerifierOutput,
)
from research_system.tools import FetchPageTool, WebSearchTool


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
                },
                {
                    "id": "operations",
                    "title": "Operations",
                    "section_type": "operations",
                    "priority": "medium",
                },
                {
                    "id": "strategy",
                    "title": "Current Direction",
                    "section_type": "strategy",
                    "priority": "medium",
                },
                {
                    "id": "risks",
                    "title": "Risks",
                    "section_type": "risks",
                    "priority": "medium",
                },
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
                    "focus": "external context",
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
    source_types = {
        "researcher_a": ("official_doc", "annual_report"),
        "researcher_b": ("news", "reference"),
        "researcher_c": ("critical_source", "paper"),
    }[prefix]
    summary = (
        "Risk and criticism note tied to sources."
        if prefix == "researcher_c"
        else "Summary tied to sources."
    )
    return {
        "agent_role": role,
        "assignment_focus": f"{prefix} focus",
        "sources": [
            {
                "id": f"{prefix}_source_001",
                "title": f"{prefix} Source 1",
                "url": f"https://example.org/{prefix}/1",
                "publisher": "Example",
                "source_type": source_types[0],
            },
            {
                "id": f"{prefix}_source_002",
                "title": f"{prefix} Source 2",
                "url": f"https://example.org/{prefix}/2",
                "publisher": "Example",
                "source_type": source_types[1],
            },
        ],
        "notes": [
            {
                "id": f"{prefix}_note_001",
                "researcher": f"Researcher {prefix[-1].upper()}",
                "section_id": "overview",
                "topic": "Overview",
                "summary": summary,
                "source_ids": [f"{prefix}_source_001", f"{prefix}_source_002"],
            }
        ],
        "limitations": ["Fixture output is intentionally compact."],
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
                        "severity": "low",
                        "description": "Fixture critic caution.",
                    }
                ],
            }
        ],
        "source_balance_notes": ["Fixture source balance checked."],
    }


def _verifier_payload() -> dict[str, Any]:
    return {
        "fact_checks": [
            {
                "id": f"fact_{index:03d}",
                "item": f"Fact {index}",
                "value": f"Value {index}",
                "status": "confirmed",
                "rationale": "Checked against stable fixture sources.",
                "source_ids": ["researcher_a_source_001"],
            }
            for index in range(1, 6)
        ],
        "checked_source_ids": ["researcher_a_source_001"],
        "confirmed_items": [f"Fact {index}" for index in range(1, 6)],
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
                },
                {
                    "heading": "Operations",
                    "section_type": "operations",
                    "content": "Operations content.",
                    "source_ids": ["researcher_b_source_001"],
                },
                {
                    "heading": "Current Direction",
                    "section_type": "strategy",
                    "content": "Strategy content.",
                    "source_ids": ["researcher_c_source_001"],
                },
            ],
            "timeline": [
                {
                    "year": "2020",
                    "event": "Representative milestone.",
                    "source_ids": ["researcher_a_source_001"],
                }
            ],
            "key_points": ["Point one."],
            "care_points": ["Read critical claims with care."],
            "source_list": [
                "researcher_a_source_001",
                "researcher_b_source_001",
                "researcher_c_source_001",
            ],
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
                "id": "researcher_b_source_001",
                "title": "B Source 1",
                "url": "https://example.org/researcher_b/1",
                "publisher": "Example News",
                "source_type": "news",
            },
            {
                "id": "researcher_c_source_001",
                "title": "C Source 1",
                "url": "https://example.org/researcher_c/1",
                "publisher": "Critical Example",
                "source_type": "critical_source",
            },
        ],
        "fact_checks": _verifier_payload()["fact_checks"],
    }


def _fake_llm(prompt: str, model: type):
    if model is PlannerOutput:
        return _planner_payload()
    if model is ResearcherOutput:
        if '"name": "Researcher A"' in prompt:
            return _researcher_payload("researcher_a", "researcher_a")
        if '"name": "Researcher B"' in prompt:
            return _researcher_payload("researcher_b", "researcher_b")
        return _researcher_payload("researcher_c", "researcher_c")
    if model is CriticOutput:
        return _critic_payload()
    if model is VerifierOutput:
        return _verifier_payload()
    if model is SynthesizerOutput:
        return _synthesizer_payload()
    raise AssertionError(f"unexpected model: {model}")


def _quality_result() -> SimpleNamespace:
    return SimpleNamespace(
        planner_output=PlannerOutput.model_validate(_planner_payload()),
        research_outputs=[
            ResearcherOutput.model_validate(
                _researcher_payload("researcher_a", "researcher_a")
            ),
            ResearcherOutput.model_validate(
                _researcher_payload("researcher_b", "researcher_b")
            ),
            ResearcherOutput.model_validate(
                _researcher_payload("researcher_c", "researcher_c")
            ),
        ],
        synthesizer_output=SynthesizerOutput.model_validate(_synthesizer_payload()),
    )


def test_quality_gate_rejects_short_planner_sections():
    result = _quality_result()
    result.planner_output.plan.briefing_sections = (
        result.planner_output.plan.briefing_sections[:3]
    )

    with pytest.raises(ResearchQualityError, match="at least 4 briefing sections"):
        validate_mvp_quality(result)


def test_quality_gate_rejects_missing_critical_source_family():
    result = _quality_result()
    for source in result.research_outputs[2].sources:
        source.source_type = "news"
    for source in result.synthesizer_output.sources:
        if source.source_type == "critical_source":
            source.source_type = "news"

    with pytest.raises(ResearchQualityError, match="critical source type"):
        validate_mvp_quality(result)


def test_tool_backed_end_to_end_run_uses_search_and_fetch(tmp_path: Path):
    search_calls: list[str] = []
    fetch_calls: list[str] = []
    researcher_prompts: list[str] = []

    def fake_search(query: str, limit: int):
        search_calls.append(query)
        return [
            {
                "title": "Evidence",
                "url": f"https://example.org/evidence/{len(search_calls)}",
                "snippet": "Search result snippet.",
            }
        ][:limit]

    def fake_fetch(url: str, *, timeout: float):
        fetch_calls.append(url)
        return f"Fetched evidence for {url}"

    def llm(prompt: str, model: type):
        if model is ResearcherOutput:
            researcher_prompts.append(prompt)
            assert '"tool_research"' in prompt
            assert "Fetched evidence" in prompt
        return _fake_llm(prompt, model)

    orchestrator = ResearchOrchestrator(
        llm=llm,
        output_root=tmp_path,
        tools=(
            WebSearchTool(search=fake_search),
            FetchPageTool(fetch=fake_fetch),
        ),
    )

    result = orchestrator.run("question", run_id="run_001")

    assert result.briefing_path.exists()
    assert len(researcher_prompts) == 3
    assert len(search_calls) == 3
    assert len(fetch_calls) == 3
    assert all(
        "WebSearchTool supplied" in " ".join(output.handoff_notes)
        for output in result.research_outputs
    )


def test_parallel_researchers_keep_same_storage_shape(tmp_path: Path):
    plan = ResearchPlan.model_validate(_planner_payload()["plan"])
    snapshots: dict[str, tuple[list[str], list[str], list[str]]] = {}

    for label, parallel in (("sequential", False), ("parallel", True)):
        output_root = tmp_path / label
        context = AgentContext(
            run_id="run_001",
            user_question="question",
            output_root=output_root,
        )
        context.set_artifact("plan", plan)
        orchestrator = ResearchOrchestrator(
            llm=_fake_llm,
            output_root=output_root,
            parallel_researchers=parallel,
        )

        outputs = orchestrator.run_researchers(
            plan,
            context=context,
            parallel=parallel,
        )

        artifact_keys = sorted(
            key for key in context.artifacts if key.startswith("researcher_")
        )
        filenames = sorted(path.name for path in context.run_dir.glob("*.json"))
        output_roles = [str(output.agent_role) for output in outputs]
        snapshots[label] = (artifact_keys, filenames, output_roles)

    assert snapshots["parallel"] == snapshots["sequential"]
