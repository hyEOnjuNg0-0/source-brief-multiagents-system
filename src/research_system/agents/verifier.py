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
    FactCheck,
    FactCheckStatus,
    ResearcherOutput,
    VerifierOutput,
)
from research_system.tools import Tool


PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"
MIN_FACT_CHECKS = 5


class VerifierAgent(Agent[VerifierOutput]):
    def __init__(
        self,
        *,
        llm: StructuredLLM,
        prompt_path: Path | None = None,
        tools: Sequence[Tool] = (),
    ) -> None:
        super().__init__(
            name="VerifierAgent",
            role=AgentRole.VERIFIER,
            prompt_path=prompt_path or PROMPT_DIR / "verifier.md",
            output_model=VerifierOutput,
            llm=llm,
            tools=tools,
        )

    def create_task(
        self,
        *,
        task_id: str = "verifier_task_001",
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
            description="Verify core facts for the final briefing.",
            payload={"research_artifacts": list(research_artifacts)},
            created_by=created_by,
        )

    def verify(
        self,
        *,
        context: AgentContext | None = None,
        task_id: str = "verifier_task_001",
    ) -> VerifierOutput:
        task = self.create_task(task_id=task_id)
        return self.run(task, context=context)

    def run(
        self,
        task: AgentTask,
        context: AgentContext | None = None,
    ) -> VerifierOutput:
        output = super().run(task, context=context)
        _validate_verifier_output(output, context=context)

        if context is not None:
            context.set_artifact("verifier", output)
            for message in self.create_followup_messages(output, task=task):
                context.messages.append(message)
            context.save_messages()
        return output

    def create_followup_messages(
        self,
        output: VerifierOutput,
        *,
        task: AgentTask,
    ) -> list[AgentMessage]:
        messages: list[AgentMessage] = []
        weak_checks = [
            fact_check
            for fact_check in output.fact_checks
            if fact_check.status
            in {FactCheckStatus.NEEDS_CARE, FactCheckStatus.CONFLICTING}
        ]
        for index, fact_check in enumerate(weak_checks, start=1):
            messages.append(
                AgentMessage(
                    id=f"{task.id}_followup_{index:03d}",
                    from_agent=self.name,
                    to_agent=_target_for_fact_check(fact_check),
                    message_type=AgentMessageType.FOLLOWUP_REQUEST,
                    content=(
                        f"Recheck fact '{fact_check.item}' "
                        f"({fact_check.status}): {fact_check.rationale}"
                    ),
                    related_task_id=task.id,
                )
            )
        return messages


def _validate_verifier_output(
    output: VerifierOutput,
    *,
    context: AgentContext | None,
) -> None:
    if len(output.fact_checks) < MIN_FACT_CHECKS:
        raise ValueError(f"verifier output must include at least {MIN_FACT_CHECKS} fact checks")

    available_source_ids = _collect_context_source_ids(context)
    if not available_source_ids:
        return

    missing = {
        source_id
        for fact_check in output.fact_checks
        for source_id in fact_check.source_ids
        if source_id not in available_source_ids
    }
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"fact checks reference unknown source_ids: {missing_list}")


def _collect_context_source_ids(context: AgentContext | None) -> set[str]:
    if context is None:
        return set()

    source_ids: set[str] = set()
    for artifact in context.artifacts.values():
        if isinstance(artifact, ResearcherOutput):
            source_ids.update(source.id for source in artifact.sources)
        elif isinstance(artifact, list):
            for item in artifact:
                if isinstance(item, ResearcherOutput):
                    source_ids.update(source.id for source in item.sources)
    return source_ids


def _target_for_fact_check(fact_check: FactCheck) -> str:
    text = f"{fact_check.item} {fact_check.rationale} {fact_check.notes or ''}".lower()
    if "official" in text or "annual" in text or "primary" in text:
        return "Researcher A"
    if "news" in text or "industry" in text or "analysis" in text:
        return "Researcher B"
    return "Researcher C"
