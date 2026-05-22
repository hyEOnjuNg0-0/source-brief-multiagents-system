from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from research_system.schemas import (
    BriefingSection,
    BriefingSectionSpec,
    BriefingSectionType,
    ResearcherOutput,
    SourceType,
    SynthesizerOutput,
)


class ResearchQualityError(ValueError):
    """Raised when a completed research run misses required quality gates."""


OFFICIAL_SOURCE_TYPES = {
    SourceType.OFFICIAL_DOC,
    SourceType.ANNUAL_REPORT,
    SourceType.PRESS_RELEASE,
    SourceType.PRIMARY_SOURCE,
}
EXTERNAL_SOURCE_TYPES = {
    SourceType.NEWS,
    SourceType.INDUSTRY_ANALYSIS,
    SourceType.PAPER,
    SourceType.BOOK,
    SourceType.REFERENCE,
    SourceType.BLOG,
    SourceType.SOCIAL_MEDIA,
}
CRITICAL_SOURCE_TYPES = {SourceType.CRITICAL_SOURCE}


def validate_mvp_quality(result: Any) -> None:
    """Validate the minimum source and briefing quality expected from a run."""

    failures: list[str] = []
    planner_output = getattr(result, "planner_output", None)
    research_outputs = list(getattr(result, "research_outputs", []) or [])
    synthesizer_output = getattr(result, "synthesizer_output", None)

    if planner_output is None:
        failures.append("missing planner_output")
    else:
        sections = planner_output.plan.briefing_sections
        failures.extend(_validate_planner_sections(sections))

    failures.extend(_validate_research_outputs(research_outputs))
    failures.extend(_validate_source_mix(research_outputs, synthesizer_output))

    if synthesizer_output is None:
        failures.append("missing synthesizer_output")
    else:
        failures.extend(_validate_final_briefing(synthesizer_output))

    if failures:
        raise ResearchQualityError(
            "Research output failed MVP quality gates: " + "; ".join(failures)
        )


def _validate_planner_sections(
    sections: Sequence[BriefingSectionSpec],
) -> list[str]:
    if len(sections) < 4:
        return [
            "planner must define at least 4 briefing sections "
            f"(found {len(sections)})"
        ]
    return []


def _validate_research_outputs(
    research_outputs: Sequence[ResearcherOutput],
) -> list[str]:
    failures: list[str] = []
    for output in research_outputs:
        label = str(output.agent_role)
        if not output.sources:
            failures.append(f"{label} must include sources")
        if not output.notes:
            failures.append(f"{label} must include notes")
        if not output.limitations and not output.unknowns:
            failures.append(f"{label} must include limitations or unknowns")
    return failures


def _validate_source_mix(
    research_outputs: Sequence[ResearcherOutput],
    synthesizer_output: SynthesizerOutput | None,
) -> list[str]:
    source_types = {
        source.source_type
        for source in _iter_sources(research_outputs, synthesizer_output)
    }
    failures: list[str] = []

    if len(source_types) < 3:
        failures.append(
            "overall sources must include at least 3 source types "
            f"(found {len(source_types)})"
        )
    if not source_types.intersection(OFFICIAL_SOURCE_TYPES):
        failures.append("sources must include at least one official source type")
    if not source_types.intersection(EXTERNAL_SOURCE_TYPES):
        failures.append("sources must include at least one external source type")
    if not source_types.intersection(CRITICAL_SOURCE_TYPES):
        failures.append("sources must include at least one critical source type")

    return failures


def _validate_final_briefing(output: SynthesizerOutput) -> list[str]:
    briefing = output.briefing
    failures: list[str] = []
    sections = briefing.sections

    if not _has_section(sections, {BriefingSectionType.OVERVIEW}, ("overview", "개요")):
        failures.append("final briefing must include an overview section")
    if not briefing.timeline:
        failures.append("final briefing must include a timeline")
    if not _has_section(
        sections,
        {BriefingSectionType.OPERATIONS, BriefingSectionType.BUSINESS_MODEL},
        ("operations", "structure", "운영", "구조"),
    ):
        failures.append("final briefing must include operations or structure")
    if not _has_section(
        sections,
        {BriefingSectionType.STRATEGY},
        ("current direction", "direction", "strategy", "현재", "방향", "전략"),
    ):
        failures.append("final briefing must include current direction")
    if not briefing.care_points and not output.unresolved_cautions:
        failures.append("final briefing must include care points")
    if not briefing.source_list or not output.sources:
        failures.append("final briefing must include sources")

    return failures


def _has_section(
    sections: Sequence[BriefingSection],
    section_types: set[BriefingSectionType],
    heading_needles: Sequence[str],
) -> bool:
    for section in sections:
        if section.section_type in section_types:
            return True
        heading = section.heading.lower()
        if any(needle in heading for needle in heading_needles):
            return True
    return False


def _iter_sources(
    research_outputs: Sequence[ResearcherOutput],
    synthesizer_output: SynthesizerOutput | None,
) -> Iterable[Any]:
    for output in research_outputs:
        yield from output.sources
    if synthesizer_output is not None:
        yield from synthesizer_output.sources
