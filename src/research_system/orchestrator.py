from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from research_system.agents.base import StructuredLLM
from research_system.agents.critic import CriticAgent
from research_system.agents.planner import PlannerAgent
from research_system.agents.researcher import ResearcherAgent, create_default_researchers
from research_system.agents.synthesizer import SynthesizerAgent
from research_system.agents.verifier import VerifierAgent
from research_system.context import AgentContext
from research_system.llm import structured_ask_llm
from research_system.quality import validate_mvp_quality
from research_system.schemas import (
    AgentMessage,
    AgentMessageType,
    CriticOutput,
    PlannerOutput,
    ResearchAssignment,
    ResearchPlan,
    ResearcherOutput,
    SchemaModel,
    SynthesizerOutput,
    VerifierOutput,
)
from research_system.tools import FetchPageTool, Tool, WebSearchTool


@dataclass(frozen=True)
class OrchestratorResult:
    context: AgentContext
    planner_output: PlannerOutput
    research_outputs: list[ResearcherOutput]
    critic_output: CriticOutput
    verifier_output: VerifierOutput
    synthesizer_output: SynthesizerOutput
    run_dir: Path
    briefing_path: Path


class ResearchOrchestrator:
    """Run the full source-based research workflow."""

    def __init__(
        self,
        *,
        llm: StructuredLLM = structured_ask_llm,
        output_root: Path | str = Path("outputs"),
        tools: Sequence[Tool] | None = None,
        planner: PlannerAgent | None = None,
        researchers: Sequence[ResearcherAgent] | None = None,
        critic: CriticAgent | None = None,
        verifier: VerifierAgent | None = None,
        synthesizer: SynthesizerAgent | None = None,
        parallel_researchers: bool = False,
    ) -> None:
        self.llm = llm
        self.output_root = Path(output_root)
        self.tools = tuple(tools) if tools is not None else default_research_tools()
        self.planner = planner or PlannerAgent(llm=llm)
        self.researchers = list(
            researchers or create_default_researchers(llm=llm, tools=self.tools)
        )
        self.critic = critic or CriticAgent(llm=llm)
        self.verifier = verifier or VerifierAgent(llm=llm)
        self.synthesizer = synthesizer or SynthesizerAgent(llm=llm)
        self.parallel_researchers = parallel_researchers
        self._researchers_by_name = {
            researcher.name: researcher
            for researcher in self.researchers
        }

    def run(
        self,
        user_question: str,
        *,
        run_id: str | None = None,
        context: AgentContext | None = None,
        settings: Mapping[str, Any] | None = None,
    ) -> OrchestratorResult:
        if context is None:
            context_kwargs: dict[str, Any] = {
                "user_question": user_question,
                "output_root": self.output_root,
                "settings": dict(settings or {}),
            }
            if run_id is not None:
                context_kwargs["run_id"] = run_id
            context = AgentContext(**context_kwargs)
        else:
            if context.user_question != user_question:
                context.user_question = user_question
            if settings:
                context.settings.update(settings)

        context.ensure_run_dir()

        planner_output = self.planner.plan(user_question, context=context)
        self._save_json(context, "plan.json", planner_output.plan)

        research_outputs = self.run_researchers(
            planner_output.plan,
            context=context,
            parallel=_setting_enabled(
                context.settings,
                "parallel_researchers",
                self.parallel_researchers,
            ),
        )
        self._set_research_artifacts(context, research_outputs)

        critic_start = len(context.messages)
        critic_output = self.critic.critique(context=context)
        self._save_json(context, "critic.json", critic_output)
        critic_followups = self._new_followup_requests(context, critic_start)
        research_outputs.extend(
            self.run_followups(
                critic_followups,
                context=context,
                stage="critic",
                starting_index=len(research_outputs) + 1,
            )
        )
        self._set_research_artifacts(context, research_outputs)

        verifier_start = len(context.messages)
        verifier_output = self.verifier.verify(context=context)
        self._save_json(context, "verifier.json", verifier_output)
        verifier_followups = self._new_followup_requests(context, verifier_start)
        research_outputs.extend(
            self.run_followups(
                verifier_followups,
                context=context,
                stage="verifier",
                starting_index=len(research_outputs) + 1,
            )
        )
        self._set_research_artifacts(context, research_outputs)

        synthesizer_output = self.synthesizer.synthesize(context=context)

        result = OrchestratorResult(
            context=context,
            planner_output=planner_output,
            research_outputs=research_outputs,
            critic_output=critic_output,
            verifier_output=verifier_output,
            synthesizer_output=synthesizer_output,
            run_dir=context.run_dir,
            briefing_path=context.run_dir / "briefing.md",
        )
        validate_mvp_quality(result)
        context.save_messages()
        context.save_snapshot()
        return result

    def run_researchers(
        self,
        plan: ResearchPlan,
        *,
        context: AgentContext,
        parallel: bool | None = None,
    ) -> list[ResearcherOutput]:
        assignments = {
            assignment.agent: assignment
            for assignment in plan.research_assignments
        }
        use_parallel = self.parallel_researchers if parallel is None else parallel
        if use_parallel:
            return self._run_researchers_parallel(plan, assignments, context=context)

        outputs: list[ResearcherOutput] = []

        for researcher in self.researchers:
            assignment = assignments.get(researcher.name)
            output = researcher.research(
                assignment=assignment,
                context=context,
                plan_id=plan.id,
                task_id=f"{_id_prefix(researcher.name)}_task_001",
            )
            outputs.append(output)
            self._save_research_output(
                context,
                researcher=researcher,
                output=output,
            )
        return outputs

    def _run_researchers_parallel(
        self,
        plan: ResearchPlan,
        assignments: Mapping[str, ResearchAssignment],
        *,
        context: AgentContext,
    ) -> list[ResearcherOutput]:
        outputs_by_name: dict[str, ResearcherOutput] = {}
        max_workers = max(1, len(self.researchers))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    researcher.research,
                    assignment=assignments.get(researcher.name),
                    context=context.model_copy(deep=True),
                    plan_id=plan.id,
                    task_id=f"{_id_prefix(researcher.name)}_task_001",
                ): researcher
                for researcher in self.researchers
            }
            for future, researcher in futures.items():
                outputs_by_name[researcher.name] = future.result()

        outputs: list[ResearcherOutput] = []
        for researcher in self.researchers:
            output = outputs_by_name[researcher.name]
            outputs.append(output)
            context.set_artifact(_id_prefix(researcher.name), output)
            self._save_research_output(
                context,
                researcher=researcher,
                output=output,
            )
        return outputs

    def run_followups(
        self,
        followups: Sequence[AgentMessage],
        *,
        context: AgentContext,
        stage: str,
        starting_index: int = 1,
    ) -> list[ResearcherOutput]:
        outputs: list[ResearcherOutput] = []
        for offset, followup in enumerate(followups):
            researcher = self._researchers_by_name.get(followup.to_agent)
            if researcher is None:
                context.add_message(
                    from_agent="ResearchOrchestrator",
                    to_agent=followup.from_agent,
                    message_type=AgentMessageType.ERROR,
                    content=f"No researcher is registered as {followup.to_agent}.",
                    related_task_id=followup.related_task_id,
                )
                continue

            sequence = starting_index + offset
            output = researcher.research(
                assignment=_assignment_for_researcher(context, researcher.name),
                context=context,
                plan_id=_plan_id(context),
                task_id=(
                    f"{_id_prefix(researcher.name)}_{stage}_followup_{sequence:03d}"
                ),
                followup_request=followup.content,
            )
            outputs.append(output)
            self._save_research_output(
                context,
                researcher=researcher,
                output=output,
                suffix=f"{stage}_followup_{sequence:03d}",
            )
        return outputs

    def _new_followup_requests(
        self,
        context: AgentContext,
        start_index: int,
    ) -> list[AgentMessage]:
        return [
            message
            for message in context.messages[start_index:]
            if message.message_type == AgentMessageType.FOLLOWUP_REQUEST
        ]

    def _set_research_artifacts(
        self,
        context: AgentContext,
        research_outputs: Sequence[ResearcherOutput],
    ) -> None:
        context.set_artifact("research_results", list(research_outputs))
        self._save_json(context, "research_results.json", list(research_outputs))

    def _save_research_output(
        self,
        context: AgentContext,
        *,
        researcher: ResearcherAgent,
        output: ResearcherOutput,
        suffix: str | None = None,
    ) -> Path:
        filename = f"{_id_prefix(researcher.name)}"
        if suffix:
            filename = f"{filename}_{suffix}"
        return self._save_json(context, f"{filename}.json", output)

    def _save_json(
        self,
        context: AgentContext,
        filename: str,
        value: Any,
    ) -> Path:
        path = context.ensure_run_dir() / filename
        path.write_text(
            json.dumps(_to_jsonable(value), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path


def default_research_tools() -> tuple[Tool, ...]:
    return (WebSearchTool(), FetchPageTool())


def _assignment_for_researcher(
    context: AgentContext,
    researcher_name: str,
) -> ResearchAssignment | None:
    plan = context.get_artifact("plan")
    if not isinstance(plan, ResearchPlan):
        return None
    for assignment in plan.research_assignments:
        if assignment.agent == researcher_name:
            return assignment
    return None


def _plan_id(context: AgentContext) -> str | None:
    plan = context.get_artifact("plan")
    if isinstance(plan, ResearchPlan):
        return plan.id
    return None


def _setting_enabled(
    settings: Mapping[str, Any],
    key: str,
    default: bool = False,
) -> bool:
    value = settings.get(key, default)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _id_prefix(value: str) -> str:
    return "".join(
        char.lower() if char.isalnum() else "_"
        for char in value
    ).strip("_")


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, SchemaModel):
        return value.model_dump(mode="json")
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {
            str(key): _to_jsonable(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [_to_jsonable(item) for item in value]
    return value
