from research_system.schemas import (
    FactCheck,
    FinalBriefing,
    PlannerOutput,
    ResearchPlan,
    ResearcherOutput,
    Source,
    SynthesizerOutput,
)
import pytest


def test_research_plan_accepts_spec_example_shape():
    plan = ResearchPlan(
        id="plan_001",
        user_question="맥도날드라는 기업의 역사, 운영 원칙, 방향성 등에 대해 알려줘",
        research_scope={
            "target": "McDonald's Corporation",
            "target_type": "company",
            "time_range": "founding_to_present",
            "region": "global",
            "language": ["ko", "en"],
            "depth": "standard",
        },
        briefing_sections=[
            {"id": "section_001", "title": "기업 개요", "priority": "high"},
        ],
        source_requirements=["official_doc", "annual_report", "news"],
        research_assignments=[
            {
                "agent": "Researcher A",
                "focus": "공식 자료와 원문 문서",
                "required_source_types": ["official_doc", "annual_report"],
            }
        ],
    )

    assert plan.research_scope.target_type == "company"
    assert plan.briefing_sections[0].priority == "high"


def test_source_fact_check_and_final_briefing_accept_spec_shapes():
    source = Source(
        id="source_001",
        title="자료 제목",
        url="https://example.org/report",
        publisher="Example Publisher",
        published_at="2025-09-01",
        accessed_at="2026-05-22",
        source_type="annual_report",
        reliability="high",
        relevance="high",
    )
    fact = FactCheck(
        id="fact_001",
        item="창립연도",
        value="1955",
        status="confirmed",
        rationale="회사 공식 자료와 복수 참고 자료가 같은 연도를 제시한다.",
        source_ids=[source.id],
    )
    briefing = FinalBriefing(
        id="briefing_001",
        title="맥도날드 기업 브리핑",
        user_question="맥도날드라는 기업의 역사, 운영 원칙, 방향성 등에 대해 알려줘",
        executive_summary="현재 조사 결과의 핵심 요약",
        sections=[
            {
                "heading": "기업 개요",
                "content": "조사 내용을 바탕으로 작성한 본문",
                "source_ids": [source.id],
            }
        ],
        timeline=[
            {
                "year": "1955",
                "event": "Ray Kroc이 McDonald's System, Inc.를 설립",
                "source_ids": [source.id],
            }
        ],
        key_points=["프랜차이즈 모델이 글로벌 확장의 핵심이었다."],
        care_points=[fact.notes] if fact.notes else [],
        source_list=[source.id],
    )

    assert source.source_type == "annual_report"
    assert fact.status == "confirmed"
    assert briefing.sections[0].heading == "기업 개요"


def test_planner_output_wraps_plan_with_fixed_agent_role():
    plan = ResearchPlan(
        id="plan_001",
        user_question="맥도날드라는 기업의 역사, 운영 원칙, 방향성 등에 대해 알려줘",
        research_scope={"target": "McDonald's", "target_type": "company"},
        briefing_sections=[
            {
                "id": "section_001",
                "title": "기업 개요",
                "section_type": "overview",
                "priority": "high",
            }
        ],
        source_requirements=["official_doc"],
        research_assignments=[
            {
                "agent": "Researcher A",
                "focus": "공식 자료",
                "required_source_types": ["official_doc"],
            }
        ],
    )

    output = PlannerOutput(plan=plan, assumptions=["입문자 기준으로 조사한다."])

    assert output.agent_role == "planner"
    assert output.plan.briefing_sections[0].section_type == "overview"


def test_researcher_output_rejects_unknown_source_references():
    source = Source(
        id="source_001",
        title="자료 제목",
        url="https://example.org/report",
        publisher="Example Publisher",
        source_type="official_doc",
    )

    with pytest.raises(ValueError, match="unknown source_ids"):
        ResearcherOutput(
            agent_role="researcher_a",
            assignment_focus="공식 자료 조사",
            sources=[source],
            notes=[
                {
                    "id": "note_001",
                    "researcher": "Researcher A",
                    "section_id": "section_001",
                    "topic": "기업 개요",
                    "summary": "핵심 내용",
                    "source_ids": ["source_missing"],
                }
            ],
        )


def test_synthesizer_output_rejects_unknown_briefing_sources():
    source = Source(
        id="source_001",
        title="자료 제목",
        url="https://example.org/report",
        publisher="Example Publisher",
        source_type="official_doc",
    )

    with pytest.raises(ValueError, match="unknown source_ids"):
        SynthesizerOutput(
            briefing={
                "id": "briefing_001",
                "title": "맥도날드 기업 브리핑",
                "user_question": "맥도날드에 대해 알려줘",
                "executive_summary": "요약",
                "sections": [
                    {
                        "heading": "기업 개요",
                        "section_type": "overview",
                        "content": "본문",
                        "source_ids": ["source_missing"],
                    }
                ],
                "source_list": ["source_001"],
            },
            sources=[source],
        )
