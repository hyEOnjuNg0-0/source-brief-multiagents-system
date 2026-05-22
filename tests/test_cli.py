from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

from research_system.cli import _load_dotenv, _load_llm_backend, run_cli
from research_system.llm import LLMConfigurationError, reset_llm_client


class FakeOrchestrator:
    def __init__(self, *, output_root: Path) -> None:
        self.output_root = output_root

    def run(self, user_question: str, *, run_id: str | None = None):
        effective_run_id = run_id or "generated_run"
        run_dir = self.output_root / effective_run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        briefing_path = run_dir / "briefing.md"
        briefing_path.write_text(f"# {user_question}\n", encoding="utf-8")
        (run_dir / "messages.json").write_text("[]", encoding="utf-8")
        return SimpleNamespace(
            context=SimpleNamespace(run_id=effective_run_id),
            run_dir=run_dir,
            briefing_path=briefing_path,
        )


class FailingOrchestrator:
    def __init__(self, *, output_root: Path) -> None:
        self.output_root = output_root

    def run(self, user_question: str, *, run_id: str | None = None):
        raise LLMConfigurationError("No LLM client configured.")


def test_cli_runs_orchestrator_and_prints_paths(tmp_path: Path):
    stdout = StringIO()

    exit_code = run_cli(
        ["--output-root", str(tmp_path), "--run-id", "run_001", "맥도날드 역사"],
        orchestrator_factory=FakeOrchestrator,
        stdout=stdout,
    )

    assert exit_code == 0
    assert "Run id: run_001" in stdout.getvalue()
    assert (tmp_path / "run_001" / "briefing.md").exists()
    assert (tmp_path / "run_001" / "messages.json").exists()


def test_cli_can_print_json_metadata(tmp_path: Path):
    stdout = StringIO()

    exit_code = run_cli(
        [
            "--output-root",
            str(tmp_path),
            "--run-id",
            "run_001",
            "--json",
            "질문",
        ],
        orchestrator_factory=FakeOrchestrator,
        stdout=stdout,
    )

    payload = json.loads(stdout.getvalue())

    assert exit_code == 0
    assert payload["run_id"] == "run_001"
    assert payload["briefing_path"].endswith("briefing.md")


def test_cli_reports_missing_llm_configuration(tmp_path: Path):
    stderr = StringIO()

    exit_code = run_cli(
        ["--output-root", str(tmp_path), "질문"],
        orchestrator_factory=FailingOrchestrator,
        stderr=stderr,
    )

    assert exit_code == 2
    assert "No LLM client configured" in stderr.getvalue()
    assert "--llm-client" in stderr.getvalue()


def test_load_llm_backend_from_module_attribute(monkeypatch):
    backend = lambda prompt: "{}"
    module = SimpleNamespace(nested=SimpleNamespace(backend=backend))
    monkeypatch.setitem(__import__("sys").modules, "fake_llm_module", module)

    try:
        assert _load_llm_backend("fake_llm_module:nested.backend") is backend
    finally:
        reset_llm_client()


def test_load_dotenv_sets_missing_environment_values(tmp_path: Path, monkeypatch):
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "\n".join(
            [
                "OPENAI_API_KEY='sk-test'",
                "RESEARCH_SYSTEM_OPENAI_MODEL=gpt-test",
                "EXISTING_VALUE=from_file",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("RESEARCH_SYSTEM_OPENAI_MODEL", raising=False)
    monkeypatch.setenv("EXISTING_VALUE", "from_env")

    _load_dotenv(dotenv)

    assert __import__("os").environ["OPENAI_API_KEY"] == "sk-test"
    assert __import__("os").environ["RESEARCH_SYSTEM_OPENAI_MODEL"] == "gpt-test"
    assert __import__("os").environ["EXISTING_VALUE"] == "from_env"
