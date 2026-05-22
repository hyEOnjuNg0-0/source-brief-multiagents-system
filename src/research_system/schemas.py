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
    target_type: str = Field(..., min_length=1)
    time_range: str = Field(default="founding_to_present", min_length=1)
    region: str = Field(default="global", min_length=1)
    language: list[str] = Field(default_factory=lambda: ["ko", "en"], min_length=1)
    depth: ResearchDepth = ResearchDepth.STANDARD


class BriefingSectionSpec(SchemaModel):
    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    section_type: BriefingSectionType | None = None
    priority: Priority = Priority.MEDIUM


class ResearchAssignment(SchemaModel):
    agent: str = Field(..., min_length=1)
    focus: str = Field(..., min_length=1)
    required_source_types: list[SourceType] = Field(default_factory=list)


class ResearchPlan(SchemaModel):
    id: str = Field(..., min_length=1)
    user_question: str = Field(..., min_length=1)
    research_scope: ResearchScope
    briefing_sections: list[BriefingSectionSpec] = Field(..., min_length=1)
    source_requirements: list[SourceType] = Field(default_factory=list)
    research_assignments: list[ResearchAssignment] = Field(..., min_length=1)
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
