from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from research_system.agents.base import Agent, StructuredLLM
from research_system.context import AgentContext
from research_system.schemas import (
    AgentMessage,
    AgentMessageType,
    AgentRole,
    AgentTask,
    CriticOutput,
)
from research_system.tools import Tool


PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


class CriticAgent(Agent[CriticOutput]):
    def __init__(
        self,
        *,
        llm: StructuredLLM,
        prompt_path: Path | None = None,
        tools: Sequence[Tool] = (),
    ) -> None:
        super().__init__(
            name="CriticAgent",
            role=AgentRole.CRITIC,
            prompt_path=prompt_path or PROMPT_DIR / "critic.md",
            output_model=CriticOutput,
            llm=llm,
            tools=tools,
        )

    def create_task(
        self,
        *,
        task_id: str = "critic_task_001",
        research_artifacts: Sequence[str] = (
            "researcher_a",
            "researcher_b",
            "researcher_c",
        ),
        created_by: str = "orchestrator",
    ) -> AgentTask:
        return AgentTask(
            id=task_id,
            target_agent=self.name,
            description="Review research outputs for gaps, bias, and weak evidence.",
            payload={"research_artifacts": list(research_artifacts)},
            created_by=created_by,
        )

    def critique(
        self,
        *,
        context: AgentContext | None = None,
        task_id: str = "critic_task_001",
    ) -> CriticOutput:
        task = self.create_task(task_id=task_id)
        return self.run(task, context=context)

    def run(
        self,
        task: AgentTask,
        context: AgentContext | None = None,
    ) -> CriticOutput:
        output = super().run(task, context=context)
        _validate_critic_output(output)

        if context is not None:
            context.set_artifact("critic", output)
            for message in self.create_followup_messages(output, task=task):
                context.messages.append(message)
            context.save_messages()
        return output

    def create_followup_messages(
        self,
        output: CriticOutput,
        *,
        task: AgentTask,
    ) -> list[AgentMessage]:
        messages: list[AgentMessage] = []
        for index, followup in enumerate(output.recommended_followups, start=1):
            messages.append(
                AgentMessage(
                    id=f"{task.id}_followup_{index:03d}",
                    from_agent=self.name,
                    to_agent=_target_for_followup(followup),
                    message_type=AgentMessageType.FOLLOWUP_REQUEST,
                    content=followup,
                    related_task_id=task.id,
                )
            )
        return messages


def _validate_critic_output(output: CriticOutput) -> None:
    has_review_issue = any(review.issues for review in output.reviews)
    has_global_caution = bool(
        output.global_issues
        or output.source_balance_notes
        or output.missing_context
        or output.recommended_followups
    )
    if not (has_review_issue or has_global_caution):
        raise ValueError("critic output must include at least one caution")


def _target_for_followup(content: str) -> str:
    normalized = content.lower()
    if "researcher a" in normalized:
        return "Researcher A"
    if "researcher b" in normalized:
        return "Researcher B"
    if "researcher c" in normalized:
        return "Researcher C"
    return "Researcher C"
