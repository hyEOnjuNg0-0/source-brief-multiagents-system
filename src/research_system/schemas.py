from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, model_validator


class SchemaModel(BaseModel):
    """Base model for all data exchanged between agents."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
        use_enum_values=True,
    )


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ResearchDepth(StrEnum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class AgentRole(StrEnum):
    PLANNER = "planner"
    RESEARCHER_A = "researcher_a"
    RESEARCHER_B = "researcher_b"
    RESEARCHER_C = "researcher_c"
    CRITIC = "critic"
    VERIFIER = "verifier"
    SYNTHESIZER = "synthesizer"


class AgentMessageType(StrEnum):
    HANDOFF = "handoff"
    FOLLOWUP_REQUEST = "followup_request"
    FOLLOWUP_RESPONSE = "followup_response"
    NOTE = "note"
    ERROR = "error"


class BriefingSectionType(StrEnum):
    OVERVIEW = "overview"
    HISTORY = "history"
    BUSINESS_MODEL = "business_model"
    OPERATIONS = "operations"
    STRATEGY = "strategy"
    RISKS = "risks"
    SOURCES = "sources"
    OTHER = "other"


class Reliability(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class Relevance(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceType(StrEnum):
    OFFICIAL_DOC = "official_doc"
    ANNUAL_REPORT = "annual_report"
    PRESS_RELEASE = "press_release"
    PRIMARY_SOURCE = "primary_source"
    NEWS = "news"
    INDUSTRY_ANALYSIS = "industry_analysis"
    PAPER = "paper"
    BOOK = "book"
    REFERENCE = "reference"
    BLOG = "blog"
    SOCIAL_MEDIA = "social_media"
    CRITICAL_SOURCE = "critical_source"
    OTHER = "other"


class QualityIssueType(StrEnum):
    SOURCE_BIAS = "source_bias"
    SOURCE_QUALITY = "source_quality"
    STALENESS = "staleness"
    MISSING_CONTEXT = "missing_context"
    INCONSISTENCY = "inconsistency"
    OVERGENERALIZATION = "overgeneralization"
    OTHER = "other"


class FactCheckStatus(StrEnum):
    CONFIRMED = "confirmed"
    NEEDS_CARE = "needs_care"
    CONFLICTING = "conflicting"


class AgentTask(SchemaModel):
    id: str = Field(..., min_length=1)
    target_agent: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    created_by: str = Field(default="orchestrator", min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentMessage(SchemaModel):
    id: str = Field(..., min_length=1)
    from_agent: str = Field(..., min_length=1)
    to_agent: str = Field(..., min_length=1)
    message_type: AgentMessageType
    content: str = Field(..., min_length=1)
    related_task_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentMemoryItem(SchemaModel):
    id: str = Field(..., min_length=1)
    agent_name: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ResearchScope(SchemaModel):
    target: str = Field(..., min_length=1)
    alternate_names: list[str] = Field(default_factory=list)
    target_type: str = Field(..., min_length=1)
    time_range: str = Field(default="founding_to_present", min_length=1)
    region: str = Field(default="global", min_length=1)
    language: list[str] = Field(default_factory=lambda: ["ko", "en"], min_length=1)
    depth: ResearchDepth = ResearchDepth.STANDARD
    expected_depth_notes: str | None = None


class BriefingSectionSpec(SchemaModel):
    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    section_type: BriefingSectionType | None = None
    priority: Priority = Priority.MEDIUM
    purpose: str | None = None
    key_questions: list[str] = Field(default_factory=list)
    evidence_needs: list[str] = Field(default_factory=list)
    source_priority: list[str] = Field(default_factory=list)


class ResearchAssignment(SchemaModel):
    agent: str = Field(..., min_length=1)
    focus: str = Field(..., min_length=1)
    supported_section_ids: list[str] = Field(default_factory=list)
    required_source_types: list[SourceType] = Field(default_factory=list)
    what_to_find: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    source_notes: list[str] = Field(default_factory=list)
    handoff_notes: list[str] = Field(default_factory=list)


class ResearchPlan(SchemaModel):
    id: str = Field(..., min_length=1)
    user_question: str = Field(..., min_length=1)
    research_scope: ResearchScope
    briefing_sections: list[BriefingSectionSpec] = Field(..., min_length=1)
    source_requirements: list[SourceType] = Field(default_factory=list)
    research_assignments: list[ResearchAssignment] = Field(..., min_length=1)
    evidence_coordination: dict[str, Any] = Field(default_factory=dict)
    recommended_final_output_elements: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Source(SchemaModel):
    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    url: AnyUrl
    publisher: str = Field(..., min_length=1)
    author: str | None = None
    published_at: date | None = None
    accessed_at: date = Field(default_factory=date.today)
    source_type: SourceType
    reliability: Reliability = Reliability.UNKNOWN
    relevance: Relevance = Relevance.MEDIUM
    notes: str | None = None


class ResearchNote(SchemaModel):
    id: str = Field(..., min_length=1)
    researcher: str = Field(..., min_length=1)
    section_id: str = Field(..., min_length=1)
    topic: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    source_ids: list[str] = Field(..., min_length=1)
    confidence: Reliability = Reliability.UNKNOWN
    limitations: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)


class QualityIssue(SchemaModel):
    type: QualityIssueType
    severity: Priority
    description: str = Field(..., min_length=1)


class QualityReview(SchemaModel):
    id: str = Field(..., min_length=1)
    target_note_id: str = Field(..., min_length=1)
    issues: list[QualityIssue] = Field(default_factory=list)
    suggested_checks: list[str] = Field(default_factory=list)


class FactCheck(SchemaModel):
    id: str = Field(..., min_length=1)
    item: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1)
    status: FactCheckStatus
    rationale: str = Field(..., min_length=1)
    source_ids: list[str] = Field(..., min_length=1)
    notes: str | None = None


class BriefingSection(SchemaModel):
    heading: str = Field(..., min_length=1)
    section_type: BriefingSectionType | None = None
    content: str = Field(..., min_length=1)
    source_ids: list[str] = Field(default_factory=list)


class TimelineEvent(SchemaModel):
    year: str = Field(..., min_length=1)
    event: str = Field(..., min_length=1)
    source_ids: list[str] = Field(default_factory=list)


class FinalBriefing(SchemaModel):
    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    user_question: str = Field(..., min_length=1)
    executive_summary: str = Field(..., min_length=1)
    sections: list[BriefingSection] = Field(..., min_length=1)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    care_points: list[str] = Field(default_factory=list)
    source_list: list[str] = Field(default_factory=list)
    method_notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PlannerOutput(SchemaModel):
    agent_role: Literal[AgentRole.PLANNER] = AgentRole.PLANNER
    plan: ResearchPlan
    assumptions: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    handoff_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_rich_planner_payload(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        if isinstance(value.get("plan"), dict):
            if _looks_like_rich_planner_payload(value["plan"]):
                return {
                    **value,
                    "plan": _normalize_research_plan_payload(value["plan"]),
                }
            return value
        if _looks_like_research_plan_payload(value):
            plan = {
                key: item
                for key, item in value.items()
                if key in ResearchPlan.model_fields
            }
            return {
                "agent_role": value.get("agent_role", AgentRole.PLANNER),
                "plan": plan,
                "assumptions": _as_string_list(value.get("assumptions")),
                "missing_inputs": _as_string_list(value.get("missing_inputs")),
                "handoff_notes": _as_string_list(value.get("handoff_notes")),
            }
        if _looks_like_rich_planner_payload(value):
            return _normalize_rich_planner_payload(value)
        return value


def _looks_like_research_plan_payload(value: dict[str, Any]) -> bool:
    return all(
        key in value
        for key in ("user_question", "research_scope", "briefing_sections")
    )


def _looks_like_rich_planner_payload(value: dict[str, Any]) -> bool:
    return any(
        key in value
        for key in (
            "user_question",
            "research_target",
            "final_briefing_shape",
            "researcher_assignments",
        )
    )


def _normalize_rich_planner_payload(value: dict[str, Any]) -> dict[str, Any]:
    plan = _normalize_research_plan_payload(value)
    return {
        "agent_role": value.get("agent_role", AgentRole.PLANNER),
        "plan": plan,
        "assumptions": _as_string_list(value.get("assumptions")),
        "missing_inputs": _as_string_list(value.get("missing_inputs")),
        "handoff_notes": _as_string_list(value.get("handoff_notes")),
    }


def _normalize_research_plan_payload(value: dict[str, Any]) -> dict[str, Any]:
    research_target = value.get("research_target")
    if not isinstance(research_target, dict):
        research_target = {}

    assignments = _normalize_research_assignments(
        value.get("researcher_assignments")
        or value.get("research_assignments")
        or value.get("assignments")
    )
    source_requirements = _unique_strings(
        source_type
        for assignment in assignments
        for source_type in assignment.get("required_source_types", [])
    )

    return {
        "id": _string_or_default(value.get("id") or value.get("plan_id"), "plan_001"),
        "user_question": _string_or_default(value.get("user_question"), "research question"),
        "research_scope": _normalize_research_scope(research_target, value),
        "briefing_sections": _normalize_briefing_sections(
            value.get("final_briefing_shape")
            or value.get("briefing_sections")
            or value.get("sections")
        ),
        "source_requirements": source_requirements,
        "research_assignments": assignments,
        "evidence_coordination": value.get("evidence_coordination") or {},
        "recommended_final_output_elements": _as_string_list(
            value.get("recommended_final_output_elements")
        ),
    }


def _normalize_research_scope(
    research_target: dict[str, Any],
    value: dict[str, Any],
) -> dict[str, Any]:
    expected_depth = (
        research_target.get("expected_depth")
        or value.get("expected_depth")
        or value.get("depth")
    )
    return {
        "target": _string_or_default(
            research_target.get("name")
            or research_target.get("target")
            or value.get("target"),
            "research target",
        ),
        "alternate_names": _as_string_list(
            research_target.get("alternate_names_to_verify")
            or research_target.get("alternate_names")
        ),
        "target_type": _string_or_default(
            research_target.get("target_type") or value.get("target_type"),
            "unknown",
        ),
        "time_range": _string_or_default(
            _format_value(research_target.get("time_range") or value.get("time_range")),
            "founding_to_present",
        ),
        "region": _string_or_default(
            research_target.get("region") or value.get("region"),
            "global",
        ),
        "language": _infer_languages(
            research_target.get("language") or value.get("language")
        ),
        "depth": _infer_depth(expected_depth),
        "expected_depth_notes": _optional_string(expected_depth),
    }


def _normalize_briefing_sections(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        value = []

    sections: list[dict[str, Any]] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            sections.append(
                {
                    "id": f"section_{index:03d}",
                    "title": str(item),
                    "priority": "medium",
                }
            )
            continue

        title = _string_or_default(item.get("title"), f"Section {index}")
        section_id = _string_or_default(
            item.get("id") or item.get("section_id"),
            f"section_{index:03d}",
        )
        sections.append(
            {
                "id": section_id,
                "title": title,
                "section_type": item.get("section_type")
                or _infer_section_type(title, item.get("purpose")),
                "priority": item.get("priority") or ("high" if index == 1 else "medium"),
                "purpose": _optional_string(item.get("purpose")),
                "key_questions": _as_string_list(item.get("key_questions")),
                "evidence_needs": _as_string_list(item.get("evidence_needs")),
                "source_priority": _as_string_list(item.get("source_priority")),
            }
        )

    if sections:
        return sections
    return [
        {
            "id": "overview",
            "title": "Overview",
            "section_type": "overview",
            "priority": "high",
        }
    ]


def _normalize_research_assignments(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        value = []

    assignments: list[dict[str, Any]] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            item = {"focus": item}

        agent = _string_or_default(
            item.get("agent") or item.get("researcher"),
            f"Researcher {chr(64 + index)}",
        )
        source_type_notes = _as_string_list(
            item.get("source_types_most_important")
            or item.get("source_priority")
            or item.get("source_types")
        )
        required_source_types = _source_types_from_any(
            item.get("required_source_types") or source_type_notes
        )
        if not required_source_types:
            required_source_types = _default_source_types_for_agent(agent)

        lane = item.get("lane") or item.get("focus")
        what_to_find = _as_string_list(item.get("what_to_find"))
        focus = _string_or_default(
            lane,
            "; ".join(what_to_find[:3]) if what_to_find else "research assignment",
        )

        assignments.append(
            {
                "agent": agent,
                "focus": focus,
                "supported_section_ids": _as_string_list(
                    item.get("primary_sections_supported")
                    or item.get("supported_section_ids")
                ),
                "required_source_types": required_source_types,
                "what_to_find": what_to_find,
                "search_queries": _as_string_list(item.get("search_queries")),
                "deliverables": _as_string_list(item.get("deliverables")),
                "source_notes": source_type_notes,
                "handoff_notes": _as_string_list(item.get("handoff_notes")),
            }
        )

    if assignments:
        return assignments
    return [
        {
            "agent": "Researcher A",
            "focus": "official and primary sources",
            "required_source_types": ["official_doc", "annual_report"],
        },
        {
            "agent": "Researcher B",
            "focus": "news and industry context",
            "required_source_types": ["news", "industry_analysis"],
        },
        {
            "agent": "Researcher C",
            "focus": "risks, criticism, and regulation",
            "required_source_types": ["critical_source"],
        },
    ]


def _infer_section_type(title: str, purpose: Any = None) -> str:
    text = f"{title} {_optional_string(purpose) or ''}".lower()
    if any(token in text for token in ("역사", "연표", "history", "timeline")):
        return "history"
    if any(token in text for token in ("운영", "구조", "포트폴리오", "operations")):
        return "operations"
    if any(token in text for token in ("방향", "비전", "전략", "인사이트", "strategy")):
        return "strategy"
    if any(token in text for token in ("리스크", "논란", "제재", "주의", "risk")):
        return "risks"
    if any(token in text for token in ("출처", "source")):
        return "sources"
    if any(token in text for token in ("개요", "한눈", "overview", "positioning")):
        return "overview"
    return "other"


def _source_types_from_any(value: Any) -> list[str]:
    return _unique_strings(
        source_type
        for item in _as_string_list(value)
        for source_type in _infer_source_types(item)
    )


def _infer_source_types(value: str) -> list[str]:
    text = value.lower()
    matches: list[str] = []
    if value in {source_type.value for source_type in SourceType}:
        matches.append(value)
    if any(token in text for token in ("공식", "official", "홈페이지", "공시", "dart")):
        matches.append("official_doc")
    if any(token in text for token in ("원문", "primary", "기관", "감독", "금융위원회", "금융감독원")):
        matches.append("primary_source")
    if any(token in text for token in ("사업보고서", "연차", "annual", "ir")):
        matches.append("annual_report")
    if any(token in text for token in ("보도자료", "press")):
        matches.append("press_release")
    if any(token in text for token in ("뉴스", "기사", "언론", "경제지", "news")):
        matches.append("news")
    if any(token in text for token in ("분석", "산업", "증권사", "신용평가", "연구기관", "analysis")):
        matches.append("industry_analysis")
    if any(token in text for token in ("비판", "리스크", "제재", "규제", "논란", "critical", "risk")):
        matches.append("critical_source")
    if any(token in text for token in ("논문", "paper")):
        matches.append("paper")
    return matches


def _default_source_types_for_agent(agent: str) -> list[str]:
    normalized = agent.strip().lower()
    if normalized.endswith("a"):
        return ["official_doc", "annual_report"]
    if normalized.endswith("b"):
        return ["news", "industry_analysis"]
    if normalized.endswith("c"):
        return ["critical_source"]
    return []


def _infer_languages(value: Any) -> list[str]:
    if isinstance(value, list):
        languages = _as_string_list(value)
        return languages or ["ko", "en"]

    text = _optional_string(value)
    if text is None:
        return ["ko", "en"]

    lowered = text.lower()
    languages: list[str] = []
    if any(token in lowered for token in ("한국", "국문", "ko", "korean")):
        languages.append("ko")
    if any(token in lowered for token in ("영문", "영어", "en", "english")):
        languages.append("en")
    return languages or [text]


def _infer_depth(value: Any) -> str:
    text = (_optional_string(value) or "").lower()
    if any(token in text for token in ("deep", "심층", "상세")):
        return "deep"
    if any(token in text for token in ("quick", "간단", "요약")):
        return "quick"
    return "standard"


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list | tuple | set):
        return [
            item
            for item in (_optional_string(item) for item in value)
            if item is not None
        ]
    text = _optional_string(value)
    return [text] if text is not None else []


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return _format_value(value)


def _string_or_default(value: Any, default: str) -> str:
    return _optional_string(value) or default


def _format_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        parts = [
            f"{key}: {formatted}"
            for key, item in value.items()
            if (formatted := _format_value(item))
        ]
        return "; ".join(parts) or None
    if isinstance(value, list | tuple | set):
        parts = [formatted for item in value if (formatted := _format_value(item))]
        return "; ".join(parts) or None
    return str(value)


def _unique_strings(values: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


class ResearcherOutput(SchemaModel):
    agent_role: Literal[
        AgentRole.RESEARCHER_A,
        AgentRole.RESEARCHER_B,
        AgentRole.RESEARCHER_C,
    ]
    assignment_focus: str = Field(..., min_length=1)
    sources: list[Source] = Field(..., min_length=1)
    notes: list[ResearchNote] = Field(..., min_length=1)
    limitations: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    handoff_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_note_sources(self) -> "ResearcherOutput":
        source_ids = {source.id for source in self.sources}
        missing = {
            source_id
            for note in self.notes
            for source_id in note.source_ids
            if source_id not in source_ids
        }
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise ValueError(f"notes reference unknown source_ids: {missing_list}")
        return self


class CriticOutput(SchemaModel):
    agent_role: Literal[AgentRole.CRITIC] = AgentRole.CRITIC
    reviews: list[QualityReview] = Field(..., min_length=1)
    global_issues: list[QualityIssue] = Field(default_factory=list)
    source_balance_notes: list[str] = Field(default_factory=list)
    missing_context: list[str] = Field(default_factory=list)
    recommended_followups: list[str] = Field(default_factory=list)
    handoff_notes: list[str] = Field(default_factory=list)


class VerifierOutput(SchemaModel):
    agent_role: Literal[AgentRole.VERIFIER] = AgentRole.VERIFIER
    fact_checks: list[FactCheck] = Field(..., min_length=1)
    checked_source_ids: list[str] = Field(default_factory=list)
    confirmed_items: list[str] = Field(default_factory=list)
    needs_care_items: list[str] = Field(default_factory=list)
    conflicting_items: list[str] = Field(default_factory=list)
    handoff_notes: list[str] = Field(default_factory=list)


class SynthesizerOutput(SchemaModel):
    agent_role: Literal[AgentRole.SYNTHESIZER] = AgentRole.SYNTHESIZER
    briefing: FinalBriefing
    sources: list[Source] = Field(..., min_length=1)
    fact_checks: list[FactCheck] = Field(default_factory=list)
    unresolved_cautions: list[str] = Field(default_factory=list)
    handoff_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_briefing_sources(self) -> "SynthesizerOutput":
        source_ids = {source.id for source in self.sources}
        referenced = set(self.briefing.source_list)
        for section in self.briefing.sections:
            referenced.update(section.source_ids)
        for event in self.briefing.timeline:
            referenced.update(event.source_ids)
        for fact_check in self.fact_checks:
            referenced.update(fact_check.source_ids)

        missing = referenced - source_ids
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise ValueError(f"briefing references unknown source_ids: {missing_list}")
        return self


# Alias with a clearer name for code that distinguishes planned sections from
# final report sections.
BriefingSectionDraft = BriefingSection
