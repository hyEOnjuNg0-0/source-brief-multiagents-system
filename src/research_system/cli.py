from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol, TextIO

from research_system.llm import LLMConfigurationError, LLMError, configure_llm_client
from research_system.orchestrator import OrchestratorResult, ResearchOrchestrator


class OrchestratorLike(Protocol):
    def run(
        self,
        user_question: str,
        *,
        run_id: str | None = None,
    ) -> OrchestratorResult:
        ...


OrchestratorFactory = Callable[..., OrchestratorLike]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m research_system.cli",
        description="Run the source-based research workflow and write a briefing.",
    )
    parser.add_argument(
        "question",
        nargs="+",
        help="Research question to investigate.",
    )
    parser.add_argument(
        "--output-root",
        default="outputs",
        help="Directory where run outputs are written. Defaults to outputs.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional run id. Defaults to a timestamp-based id.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable run metadata.",
    )
    parser.add_argument(
        "--llm-client",
        default=os.environ.get("RESEARCH_SYSTEM_LLM_CLIENT"),
        help=(
            "Python object path for the LLM backend, as module:attribute. "
            "The object must be callable or expose complete(prompt). "
            "Can also be set with RESEARCH_SYSTEM_LLM_CLIENT."
        ),
    )
    return parser


def run_cli(
    argv: Sequence[str] | None = None,
    *,
    orchestrator_factory: OrchestratorFactory = ResearchOrchestrator,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    parser = build_parser()
    args = parser.parse_args(argv)
    question = " ".join(args.question).strip()

    if not question:
        parser.print_usage(err)
        print("error: question must not be empty", file=err)
        return 2

    if args.llm_client:
        try:
            configure_llm_client(_load_llm_backend(args.llm_client))
        except (AttributeError, ImportError, ValueError) as exc:
            print(f"Could not load LLM client {args.llm_client!r}: {exc}", file=err)
            return 2
    elif os.environ.get("OPENAI_API_KEY"):
        configure_llm_client(_load_llm_backend("openai"))

    orchestrator = orchestrator_factory(output_root=Path(args.output_root))

    try:
        result = orchestrator.run(question, run_id=args.run_id)
    except LLMConfigurationError as exc:
        print(str(exc), file=err)
        print(
            "Pass --llm-client module:attribute or set "
            "RESEARCH_SYSTEM_LLM_CLIENT to configure a backend.",
            file=err,
        )
        return 2
    except LLMError as exc:
        print(f"LLM error: {exc}", file=err)
        return 1

    if args.json:
        payload = {
            "run_id": result.context.run_id,
            "run_dir": str(result.run_dir),
            "briefing_path": str(result.briefing_path),
        }
        print(json.dumps(payload, ensure_ascii=False), file=out)
    else:
        print(f"Run id: {result.context.run_id}", file=out)
        print(f"Run directory: {result.run_dir}", file=out)
        print(f"Briefing: {result.briefing_path}", file=out)

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return run_cli(argv)


def _load_llm_backend(spec: str):
    if spec in {"openai", "openai-responses", "openai_responses"}:
        from research_system.openai_backend import create_default_client

        return create_default_client()

    module_name, separator, attribute_path = spec.partition(":")
    if not separator or not module_name or not attribute_path:
        raise ValueError("expected format module:attribute")

    target = importlib.import_module(module_name)
    for attribute in attribute_path.split("."):
        if not attribute:
            raise ValueError("attribute path must not contain empty parts")
        target = getattr(target, attribute)
    return target


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
