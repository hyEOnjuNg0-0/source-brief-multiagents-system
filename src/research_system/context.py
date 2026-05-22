from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import Field

from research_system.schemas import AgentMessage, AgentMessageType, SchemaModel


class AgentContext(SchemaModel):
    """Shared state for one research run."""

    run_id: str = Field(default_factory=lambda: _new_run_id(), min_length=1)
    user_question: str = Field(..., min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    output_root: Path = Field(default=Path("outputs"))
    artifacts: dict[str, Any] = Field(default_factory=dict)
    messages: list[AgentMessage] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)

    @property
    def run_dir(self) -> Path:
        return self.output_root / self.run_id

    def ensure_run_dir(self) -> Path:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        return self.run_dir

    def set_artifact(self, name: str, value: Any) -> None:
        if not name.strip():
            raise ValueError("artifact name must not be empty")
        self.artifacts[name] = value

    def get_artifact(self, name: str, default: Any = None) -> Any:
        return self.artifacts.get(name, default)

    def add_message(
        self,
        *,
        from_agent: str,
        to_agent: str,
        message_type: AgentMessageType | str,
        content: str,
        related_task_id: str | None = None,
        message_id: str | None = None,
        persist: bool = True,
    ) -> AgentMessage:
        message = AgentMessage(
            id=message_id or f"message_{len(self.messages) + 1:04d}",
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            related_task_id=related_task_id,
        )
        self.messages.append(message)
        if persist:
            self.save_messages()
        return message

    def save_messages(self, path: Path | None = None) -> Path:
        target = path or self.run_dir / "messages.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                [message.model_dump(mode="json") for message in self.messages],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return target

    def save_snapshot(self, path: Path | None = None) -> Path:
        target = path or self.run_dir / "context.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_jsonable(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "user_question": self.user_question,
            "created_at": self.created_at.isoformat(),
            "output_root": str(self.output_root),
            "artifacts": _to_jsonable(self.artifacts),
            "messages": [
                message.model_dump(mode="json")
                for message in self.messages
            ],
            "settings": _to_jsonable(self.settings),
        }


def _new_run_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{uuid4().hex[:8]}"


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
