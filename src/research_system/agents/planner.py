from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from research_system.agents.base import Agent, StructuredLLM
from research_system.context import AgentContext
from research_system.schemas import (
    AgentMessageType,
    AgentRole,
    AgentTask,
    PlannerOutput,
)
from research_system.tools import Tool


PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


class PlannerAgent(Agent[PlannerOutput]):
    def __init__(
        self,
        *,
        llm: StructuredLLM,
        prompt_path: Path | None = None,
        tools: Sequence[Tool] = (),
    ) -> None:
        super().__init__(
            name="PlannerAgent",
            role=AgentRole.PLANNER,
            prompt_path=prompt_path or PROMPT_DIR / "planner.md",
            output_model=PlannerOutput,
            llm=llm,
            tools=tools,
        )

    def create_task(
        self,
        user_question: str,
        *,
        task_id: str = "planner_task_001",
        created_by: str = "orchestrator",
    ) -> AgentTask:
        return AgentTask(
            id=task_id,
            target_agent=self.name,
            description="Create a source-based research plan for the user question.",
            payload={"user_question": user_question},
            created_by=created_by,
        )

    def plan(
        self,
        user_question: str,
        *,
        context: AgentContext | None = None,
        task_id: str = "planner_task_001",
    ) -> PlannerOutput:
        task = self.create_task(user_question, task_id=task_id)
        return self.run(task, context=context)

    def run(
        self,
        task: AgentTask,
        context: AgentContext | None = None,
    ) -> PlannerOutput:
        output = super().run(task, context=context)
        _validate_planner_output(output)

        if context is not None:
            context.set_artifact("plan", output.plan)
            context.set_artifact("planner_output", output)
            context.add_message(
                from_agent=self.name,
                to_agent="ResearcherAgents",
                message_type=AgentMessageType.HANDOFF,
                content=(
                    "Created research plan "
                    f"{output.plan.id} with "
                    f"{len(output.plan.research_assignments)} assignments."
                ),
                related_task_id=task.id,
            )
        return output


def _validate_planner_output(output: PlannerOutput) -> None:
    assignments = output.plan.research_assignments
    agents = {assignment.agent for assignment in assignments}
    required = {"Researcher A", "Researcher B", "Researcher C"}
    missing = required - agents
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"plan is missing researcher assignments: {missing_list}")

    focuses = {
        assignment.focus.strip().lower()
        for assignment in assignments
    }
    if len(focuses) != len(assignments):
        raise ValueError("researcher assignment focuses must be distinct")
