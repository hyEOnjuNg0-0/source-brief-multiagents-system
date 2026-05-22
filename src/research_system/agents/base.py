from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, Mapping, Protocol, Sequence, TypeVar

from research_system.llm import structured_ask_llm
from research_system.schemas import (
    AgentMemoryItem,
    AgentRole,
    AgentTask,
    SchemaModel,
)
from research_system.tools import Tool

OutputT = TypeVar("OutputT", bound=SchemaModel)


class StructuredLLM(Protocol):
    def __call__(self, prompt: str, output_model: type[OutputT]) -> OutputT:
        ...


@dataclass
class Agent(Generic[OutputT]):
    name: str
    role: AgentRole
    prompt_path: Path
    output_model: type[OutputT]
    llm: StructuredLLM = structured_ask_llm
    tools: Sequence[Tool] = field(default_factory=tuple)
    memory: list[AgentMemoryItem] = field(default_factory=list)

    def run(
        self,
        task: AgentTask,
        context: Mapping[str, Any] | SchemaModel | None = None,
    ) -> OutputT:
        prompt = self.build_prompt(task=task, context=context)
        raw_output = self.llm(prompt, self.output_model)
        output = self.output_model.model_validate(raw_output)
        self.remember(
            content=f"Completed task {task.id}",
            metadata={"task_id": task.id, "output_model": self.output_model.__name__},
        )
        return output

    def build_prompt(
        self,
        task: AgentTask,
        context: Mapping[str, Any] | SchemaModel | None = None,
    ) -> str:
        parts = [
            self.load_prompt(),
            "## Agent",
            json.dumps(
                {"name": self.name, "role": self.role},
                ensure_ascii=False,
                indent=2,
            ),
            "## Task",
            task.model_dump_json(indent=2),
        ]

        if context is not None:
            parts.extend(["## Context", self._serialize_context(context)])

        if self.tools:
            parts.extend(["## Available Tools", self._serialize_tools()])

        if self.memory:
            parts.extend(["## Short Memory", self._serialize_memory()])

        parts.extend(
            [
                "## Output Contract",
                f"Return JSON that validates as {self.output_model.__name__}.",
            ]
        )

        return "\n\n".join(parts)

    def load_prompt(self) -> str:
        return self.prompt_path.read_text(encoding="utf-8").strip()

    def remember(
        self,
        content: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> AgentMemoryItem:
        item = AgentMemoryItem(
            id=f"{self._id_prefix()}_memory_{len(self.memory) + 1}",
            agent_name=self.name,
            content=content,
            metadata=dict(metadata or {}),
        )
        self.memory.append(item)
        return item

    def _serialize_context(self, context: Mapping[str, Any] | SchemaModel) -> str:
        if isinstance(context, SchemaModel):
            return context.model_dump_json(indent=2)
        return json.dumps(context, ensure_ascii=False, indent=2, default=str)

    def _serialize_tools(self) -> str:
        tools = [
            {"name": tool.name, "description": tool.description}
            for tool in self.tools
        ]
        return json.dumps(tools, ensure_ascii=False, indent=2)

    def _serialize_memory(self) -> str:
        return json.dumps(
            [item.model_dump(mode="json") for item in self.memory],
            ensure_ascii=False,
            indent=2,
        )

    def _id_prefix(self) -> str:
        return "".join(
            char.lower() if char.isalnum() else "_"
            for char in self.name
        ).strip("_")
