from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from research_system.agents.base import Agent, StructuredLLM
from research_system.context import AgentContext
from research_system.schemas import (
    AgentRole,
    AgentTask,
    BriefingSection,
    FactCheck,
    FinalBriefing,
    Source,
    SynthesizerOutput,
)
from research_system.tools import Tool


PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


class SynthesizerAgent(Agent[SynthesizerOutput]):
    def __init__(
        self,
        *,
        llm: StructuredLLM,
        prompt_path: Path | None = None,
        tools: Sequence[Tool] = (),
    ) -> None:
        super().__init__(
            name="SynthesizerAgent",
            role=AgentRole.SYNTHESIZER,
            prompt_path=prompt_path or PROMPT_DIR / "synthesizer.md",
            output_model=SynthesizerOutput,
            llm=llm,
            tools=tools,
        )

    def create_task(
        self,
        *,
        task_id: str = "synthesizer_task_001",
        required_artifacts: Sequence[str] = (
            "plan",
            "researcher_a",
            "researcher_b",
            "researcher_c",
            "critic",
            "verifier",
        ),
        created_by: str = "orchestrator",
    ) -> AgentTask:
        return AgentTask(
            id=task_id,
            target_agent=self.name,
            description="Synthesize all research outputs into a final briefing.",
            payload={"required_artifacts": list(required_artifacts)},
            created_by=created_by,
        )

    def synthesize(
        self,
        *,
        context: AgentContext | None = None,
        task_id: str = "synthesizer_task_001",
    ) -> SynthesizerOutput:
        task = self.create_task(task_id=task_id)
        return self.run(task, context=context)

    def run(
        self,
        task: AgentTask,
        context: AgentContext | None = None,
    ) -> SynthesizerOutput:
        output = super().run(task, context=context)
        _validate_synthesizer_output(output)

        if context is not None:
            context.set_artifact("briefing", output.briefing)
            context.set_artifact("synthesizer", output)
            _write_briefing_outputs(context, output)
        return output


def briefing_to_markdown(output: SynthesizerOutput) -> str:
    briefing = output.briefing
    parts = [
        f"# {briefing.title}",
        "",
        "## Executive Summary",
        briefing.executive_summary,
        "",
    ]

    if briefing.key_points:
        parts.extend(["## Key Points", *_bullet_list(briefing.key_points), ""])

    if briefing.sections:
        parts.append("## Sections")
        for section in briefing.sections:
            parts.extend(_section_to_markdown(section))

    if briefing.timeline:
        parts.extend(["## Timeline"])
        for event in briefing.timeline:
            source_text = _source_refs(event.source_ids)
            parts.append(f"- {event.year}: {event.event}{source_text}")
        parts.append("")

    if output.fact_checks:
        parts.extend(["## Verified Facts"])
        for fact_check in output.fact_checks:
            parts.append(_fact_check_to_markdown(fact_check))
        parts.append("")

    care_points = list(briefing.care_points) + list(output.unresolved_cautions)
    if care_points:
        parts.extend(["## Read With Care", *_bullet_list(care_points), ""])

    parts.extend(["## Sources"])
    source_ids = _ordered_source_ids(briefing, output.fact_checks)
    sources_by_id = {source.id: source for source in output.sources}
    for source_id in source_ids:
        source = sources_by_id.get(source_id)
        if source is not None:
            parts.append(_source_to_markdown(source))
    parts.append("")

    if briefing.method_notes:
        parts.extend(["## Method Notes", briefing.method_notes, ""])

    return "\n".join(parts).strip() + "\n"


def _write_briefing_outputs(
    context: AgentContext,
    output: SynthesizerOutput,
) -> tuple[Path, Path]:
    run_dir = context.ensure_run_dir()
    json_path = run_dir / "briefing.json"
    markdown_path = run_dir / "briefing.md"

    json_path.write_text(
        json.dumps(output.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown_path.write_text(briefing_to_markdown(output), encoding="utf-8")
    return json_path, markdown_path


def _validate_synthesizer_output(output: SynthesizerOutput) -> None:
    if not output.briefing.care_points and not output.unresolved_cautions:
        raise ValueError("synthesizer output must include at least one care point")
    if not output.briefing.source_list:
        raise ValueError("synthesizer output must include a source list")


def _section_to_markdown(section: BriefingSection) -> list[str]:
    source_text = _source_refs(section.source_ids)
    return [
        f"### {section.heading}",
        section.content,
        f"Sources: {source_text.strip()}" if source_text else "Sources: none",
        "",
    ]


def _fact_check_to_markdown(fact_check: FactCheck) -> str:
    source_text = _source_refs(fact_check.source_ids)
    return (
        f"- {fact_check.status}: {fact_check.item} = {fact_check.value}. "
        f"{fact_check.rationale}{source_text}"
    )


def _source_to_markdown(source: Source) -> str:
    dates = []
    if source.published_at:
        dates.append(f"published {source.published_at.isoformat()}")
    if source.accessed_at:
        dates.append(f"accessed {source.accessed_at.isoformat()}")
    date_text = f" ({', '.join(dates)})" if dates else ""
    return (
        f"- `{source.id}`: {source.title}. {source.publisher}. "
        f"{source.url}{date_text}"
    )


def _ordered_source_ids(
    briefing: FinalBriefing,
    fact_checks: Sequence[FactCheck],
) -> list[str]:
    ordered: list[str] = []
    for source_id in briefing.source_list:
        _append_unique(ordered, source_id)
    for section in briefing.sections:
        for source_id in section.source_ids:
            _append_unique(ordered, source_id)
    for event in briefing.timeline:
        for source_id in event.source_ids:
            _append_unique(ordered, source_id)
    for fact_check in fact_checks:
        for source_id in fact_check.source_ids:
            _append_unique(ordered, source_id)
    return ordered


def _append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _source_refs(source_ids: Sequence[str]) -> str:
    if not source_ids:
        return ""
    return " [" + ", ".join(source_ids) + "]"


def _bullet_list(items: Sequence[str]) -> list[str]:
    return [f"- {item}" for item in items]
