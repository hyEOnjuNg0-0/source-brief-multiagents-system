from __future__ import annotations

import json
from pathlib import Path

from research_system.agents.synthesizer import SynthesizerAgent
from research_system.context import AgentContext
from research_system.schemas import AgentMessageType
from research_system.tools import SaveArtifactTool


def _synthesizer_payload() -> dict:
    return {
        "briefing": {
            "id": "briefing_001",
            "title": "Artifact Briefing",
            "user_question": "question",
            "executive_summary": "Summary with source references.",
            "sections": [
                {
                    "heading": "Overview",
                    "section_type": "overview",
                    "content": "Sourced overview.",
                    "source_ids": ["source_001"],
                }
            ],
            "key_points": ["Point one."],
            "care_points": ["Current details may change."],
            "source_list": ["source_001", "source_002"],
        },
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
                "title": "News page",
                "url": "https://example.org/news",
                "publisher": "Example News",
                "source_type": "news",
            },
        ],
        "fact_checks": [
            {
                "id": "fact_001",
                "item": "Core fact",
                "value": "Known value",
                "status": "confirmed",
                "rationale": "Checked against sources.",
                "source_ids": ["source_001"],
            }
        ],
        "unresolved_cautions": [],
    }


def test_run_artifacts_include_json_markdown_messages_and_snapshot(tmp_path: Path):
    context = AgentContext(
        run_id="run_001",
        user_question="question",
        output_root=tmp_path,
    )
    context.add_message(
        from_agent="PlannerAgent",
        to_agent="ResearcherAgents",
        message_type=AgentMessageType.HANDOFF,
        content="Plan is ready.",
    )
    SaveArtifactTool().run(
        name="plan",
        content={"id": "plan_001"},
        context=context,
    )

    SynthesizerAgent(llm=lambda prompt, model: _synthesizer_payload()).synthesize(
        context=context
    )
    context.save_snapshot()

    run_dir = tmp_path / "run_001"
    assert json.loads((run_dir / "plan.json").read_text(encoding="utf-8")) == {
        "id": "plan_001"
    }
    assert json.loads((run_dir / "messages.json").read_text(encoding="utf-8"))[0][
        "message_type"
    ] == "handoff"
    assert json.loads((run_dir / "briefing.json").read_text(encoding="utf-8"))[
        "briefing"
    ]["id"] == "briefing_001"
    assert "# Artifact Briefing" in (run_dir / "briefing.md").read_text(
        encoding="utf-8"
    )
    snapshot = json.loads((run_dir / "context.json").read_text(encoding="utf-8"))
    assert snapshot["artifacts"]["briefing"]["id"] == "briefing_001"
