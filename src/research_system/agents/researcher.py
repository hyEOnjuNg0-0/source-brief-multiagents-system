from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from research_system.agents.base import Agent, StructuredLLM
from research_system.context import AgentContext
from research_system.schemas import (
    AgentMessageType,
    AgentRole,
    AgentTask,
    ResearchAssignment,
    ResearchPlan,
    ResearcherOutput,
    SourceType,
)
from research_system.tools import Tool


PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"

RESEARCHER_PROMPTS = {
    AgentRole.RESEARCHER_A: PROMPT_DIR / "researcher_a.md",
    AgentRole.RESEARCHER_B: PROMPT_DIR / "researcher_b.md",
    AgentRole.RESEARCHER_C: PROMPT_DIR / "researcher_c.md",
}

DEFAULT_FOCUS = {
    AgentRole.RESEARCHER_A: "official sources and primary documents",
    AgentRole.RESEARCHER_B: "news, industry analysis, and explanatory context",
    AgentRole.RESEARCHER_C: "critical perspectives, risks, regulation, and limits",
}

ROLE_EXPECTED_SOURCE_TYPES = {
    AgentRole.RESEARCHER_A: {
        SourceType.OFFICIAL_DOC,
        SourceType.ANNUAL_REPORT,
        SourceType.PRESS_RELEASE,
        SourceType.PRIMARY_SOURCE,
    },
    AgentRole.RESEARCHER_B: {
        SourceType.NEWS,
        SourceType.INDUSTRY_ANALYSIS,
        SourceType.REFERENCE,
    },
    AgentRole.RESEARCHER_C: {
        SourceType.CRITICAL_SOURCE,
        SourceType.PAPER,
        SourceType.NEWS,
        SourceType.OTHER,
    },
}

RISK_OR_CRITICISM_KEYWORDS = (
    "risk",
    "risks",
    "criticism",
    "criticisms",
    "critical",
    "concern",
    "concerns",
    "controversy",
    "controversies",
    "limitation",
    "limitations",
    "regulation",
    "regulatory",
    "비판",
    "리스크",
    "위험",
    "우려",
    "논란",
    "한계",
    "규제",
)


class ResearcherAgent(Agent[ResearcherOutput]):
    def __init__(
        self,
        *,
        name: str,
        role: AgentRole,
        llm: StructuredLLM,
        focus: str | None = None,
        prompt_path: Path | None = None,
        tools: Sequence[Tool] = (),
    ) -> None:
        if role not in RESEARCHER_PROMPTS:
            raise ValueError(f"unsupported researcher role: {role}")
        super().__init__(
            name=name,
            role=role,
            prompt_path=prompt_path or RESEARCHER_PROMPTS[role],
            output_model=ResearcherOutput,
            llm=llm,
            tools=tools,
        )
        self.focus = focus or DEFAULT_FOCUS[role]

    def create_task(
        self,
        *,
        assignment: ResearchAssignment | None = None,
        plan_id: str | None = None,
        task_id: str | None = None,
        followup_request: str | None = None,
        created_by: str = "orchestrator",
    ) -> AgentTask:
        effective_focus = assignment.focus if assignment is not None else self.focus
        payload = {
            "agent_name": self.name,
            "agent_role": self.role,
            "focus": effective_focus,
            "plan_id": plan_id,
            "followup_request": followup_request,
        }
        if assignment is not None:
            payload["assignment"] = assignment.model_dump(mode="json")

        return AgentTask(
            id=task_id or f"{_id_prefix(self.name)}_task_001",
            target_agent=self.name,
            description="Collect source-based research notes for the assigned focus.",
            payload=payload,
            created_by=created_by,
        )

    def research(
        self,
        *,
        assignment: ResearchAssignment | None = None,
        context: AgentContext | None = None,
        plan_id: str | None = None,
        task_id: str | None = None,
        followup_request: str | None = None,
    ) -> ResearcherOutput:
        task = self.create_task(
            assignment=assignment,
            plan_id=plan_id,
            task_id=task_id,
            followup_request=followup_request,
        )
        return self.run(task, context=context)

    def run(
        self,
        task: AgentTask,
        context: AgentContext | None = None,
    ) -> ResearcherOutput:
        output = super().run(task, context=context)
        _validate_researcher_output(self, output, task=task, context=context)

        if context is not None:
            artifact_name = _id_prefix(self.name)
            context.set_artifact(artifact_name, output)
            if task.payload.get("followup_request"):
                context.add_message(
                    from_agent=self.name,
                    to_agent=task.created_by,
                    message_type=AgentMessageType.FOLLOWUP_RESPONSE,
                    content=(
                        "Completed follow-up research with "
                        f"{len(output.sources)} sources and "
                        f"{len(output.notes)} notes."
                    ),
                    related_task_id=task.id,
                )
        return output


def create_default_researchers(
    *,
    llm: StructuredLLM,
    tools: Sequence[Tool] = (),
) -> list[ResearcherAgent]:
    return [
        ResearcherAgent(
            name="Researcher A",
            role=AgentRole.RESEARCHER_A,
            llm=llm,
            tools=tools,
        ),
        ResearcherAgent(
            name="Researcher B",
            role=AgentRole.RESEARCHER_B,
            llm=llm,
            tools=tools,
        ),
        ResearcherAgent(
            name="Researcher C",
            role=AgentRole.RESEARCHER_C,
            llm=llm,
            tools=tools,
        ),
    ]


def _validate_researcher_output(
    agent: ResearcherAgent,
    output: ResearcherOutput,
    *,
    task: AgentTask,
    context: AgentContext | None,
) -> None:
    if output.agent_role != agent.role:
        raise ValueError(
            f"{agent.name} returned agent_role {output.agent_role!r}, "
            f"expected {agent.role!r}"
        )
    if len(output.sources) < 2:
        raise ValueError(f"{agent.name} must include at least two sources")

    assignment = _assignment_from_task(task)
    if assignment is not None:
        _validate_required_source_types(agent, output, assignment)

    _validate_role_source_types(agent, output)
    _validate_note_sections(agent, output, context)

    if agent.role == AgentRole.RESEARCHER_C and not _has_risk_or_criticism_note(output):
        raise ValueError(
            "Researcher C must include risk or criticism notes in its research output"
        )


def _assignment_from_task(task: AgentTask) -> ResearchAssignment | None:
    assignment = task.payload.get("assignment")
    if assignment is None:
        return None
    return ResearchAssignment.model_validate(assignment)


def _validate_required_source_types(
    agent: ResearcherAgent,
    output: ResearcherOutput,
    assignment: ResearchAssignment,
) -> None:
    required = {
        _source_type_value(source_type)
        for source_type in assignment.required_source_types
    }
    if not required:
        return

    actual = _source_type_values(output)
    missing = required - actual
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(
            f"{agent.name} is missing required source types: {missing_list}"
        )


def _validate_role_source_types(
    agent: ResearcherAgent,
    output: ResearcherOutput,
) -> None:
    expected = {
        _source_type_value(source_type)
        for source_type in ROLE_EXPECTED_SOURCE_TYPES[agent.role]
    }
    actual = _source_type_values(output)
    if actual.isdisjoint(expected):
        expected_list = ", ".join(sorted(expected))
        raise ValueError(
            f"{agent.name} must include at least one role-appropriate source "
            f"type: {expected_list}"
        )


def _validate_note_sections(
    agent: ResearcherAgent,
    output: ResearcherOutput,
    context: AgentContext | None,
) -> None:
    section_ids = _planned_section_ids(context)
    if not section_ids:
        return

    unknown = {
        note.section_id
        for note in output.notes
        if note.section_id not in section_ids
    }
    if unknown:
        unknown_list = ", ".join(sorted(unknown))
        raise ValueError(
            f"{agent.name} notes reference unknown planner section_ids: "
            f"{unknown_list}"
        )


def _planned_section_ids(context: AgentContext | None) -> set[str]:
    if context is None:
        return set()

    plan = context.get_artifact("plan")
    if not isinstance(plan, ResearchPlan):
        return set()
    return {section.id for section in plan.briefing_sections}


def _has_risk_or_criticism_note(output: ResearcherOutput) -> bool:
    texts: list[str] = []
    for note in output.notes:
        texts.extend([note.topic, note.summary, *note.limitations, *note.unknowns])
    texts.extend([*output.limitations, *output.unknowns, *output.handoff_notes])
    normalized = " ".join(texts).lower()
    return any(keyword in normalized for keyword in RISK_OR_CRITICISM_KEYWORDS)


def _source_type_values(output: ResearcherOutput) -> set[str]:
    return {_source_type_value(source.source_type) for source in output.sources}


def _source_type_value(source_type: SourceType | str) -> str:
    return str(source_type)


def _id_prefix(value: str) -> str:
    return "".join(
        char.lower() if char.isalnum() else "_"
        for char in value
    ).strip("_")
