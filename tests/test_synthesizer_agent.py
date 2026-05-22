from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_system.agents.synthesizer import SynthesizerAgent, briefing_to_markdown
from research_system.context import AgentContext


def _synthesizer_payload() -> dict:
    return {
        "briefing": {
            "id": "briefing_001",
            "title": "Company Briefing",
            "user_question": "question",
            "executive_summary": "Summary with sourced conclusions.",
            "sections": [
                {
                    "heading": "Overview",
                    "section_type": "overview",
                    "content": "Overview content.",
                    "source_ids": ["source_001"],
                }
            ],
            "timeline": [
                {
                    "year": "1955",
                    "event": "Important event.",
                    "source_ids": ["source_001"],
                }
            ],
            "key_points": ["Point one."],
            "care_points": ["Some claims need careful reading."],
            "source_list": ["source_001", "source_002"],
            "method_notes": "Compiled from intermediate agent outputs.",
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
                "item": "Founding year",
                "value": "1955",
                "status": "confirmed",
                "rationale": "Sources agree.",
                "source_ids": ["source_001"],
            }
        ],
        "unresolved_cautions": ["Current details may change."],
    }


def test_synthesizer_agent_writes_briefing_files(tmp_path: Path):
    agent = SynthesizerAgent(llm=lambda prompt, model: _synthesizer_payload())
    context = AgentContext(
        run_id="run_001",
        user_question="question",
        output_root=tmp_path,
    )

    output = agent.synthesize(context=context)

    briefing_json = tmp_path / "run_001" / "briefing.json"
    briefing_md = tmp_path / "run_001" / "briefing.md"

    assert context.get_artifact("briefing") == output.briefing
    assert json.loads(briefing_json.read_text(encoding="utf-8"))["briefing"]["id"] == "briefing_001"
    markdown = briefing_md.read_text(encoding="utf-8")
    assert "# Company Briefing" in markdown
    assert "## Read With Care" in markdown
    assert "`source_001`" in markdown


def test_briefing_to_markdown_includes_sections_facts_and_sources():
    agent = SynthesizerAgent(llm=lambda prompt, model: _synthesizer_payload())
    output = agent.synthesize()

    markdown = briefing_to_markdown(output)

    assert "### Overview" in markdown
    assert "Founding year = 1955" in markdown
    assert "https://example.org/official" in markdown


def test_synthesizer_agent_requires_care_points():
    payload = _synthesizer_payload()
    payload["briefing"]["care_points"] = []
    payload["unresolved_cautions"] = []
    agent = SynthesizerAgent(llm=lambda prompt, model: payload)

    with pytest.raises(ValueError, match="care point"):
        agent.synthesize()
