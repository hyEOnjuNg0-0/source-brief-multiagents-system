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
    ResearcherOutput,
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
        _validate_researcher_output(self, output)

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
) -> None:
    if output.agent_role != agent.role:
        raise ValueError(
            f"{agent.name} returned agent_role {output.agent_role!r}, "
            f"expected {agent.role!r}"
        )
    if len(output.sources) < 2:
        raise ValueError(f"{agent.name} must include at least two sources")


def _id_prefix(value: str) -> str:
    return "".join(
        char.lower() if char.isalnum() else "_"
        for char in value
    ).strip("_")
