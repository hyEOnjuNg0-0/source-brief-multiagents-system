import json
from pathlib import Path

from research_system.context import AgentContext
from research_system.schemas import AgentMessageType


def test_agent_context_persists_messages_json(tmp_path: Path):
    context = AgentContext(
        run_id="run_001",
        user_question="조사 질문",
        output_root=tmp_path,
    )

    message = context.add_message(
        from_agent="CriticAgent",
        to_agent="Researcher C",
        message_type=AgentMessageType.FOLLOWUP_REQUEST,
        content="최근 규제 이슈 출처를 보완해줘.",
        related_task_id="task_001",
    )

    messages_path = tmp_path / "run_001" / "messages.json"
    saved = json.loads(messages_path.read_text(encoding="utf-8"))

    assert message.id == "message_0001"
    assert saved == [
        {
            "id": "message_0001",
            "from_agent": "CriticAgent",
            "to_agent": "Researcher C",
            "message_type": "followup_request",
            "content": "최근 규제 이슈 출처를 보완해줘.",
            "related_task_id": "task_001",
            "created_at": message.created_at.isoformat().replace("+00:00", "Z"),
        }
    ]


def test_agent_context_tracks_artifacts_and_snapshot(tmp_path: Path):
    context = AgentContext(
        run_id="run_001",
        user_question="조사 질문",
        output_root=tmp_path,
    )

    context.set_artifact("plan", {"id": "plan_001"})
    snapshot_path = context.save_snapshot()
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))

    assert context.get_artifact("plan") == {"id": "plan_001"}
    assert snapshot["run_id"] == "run_001"
    assert snapshot["artifacts"]["plan"] == {"id": "plan_001"}
