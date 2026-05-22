from __future__ import annotations

from pathlib import Path

import pytest

from research_system.agents.planner import PlannerAgent
from research_system.context import AgentContext
from research_system.schemas import PlannerOutput


def _planner_payload() -> dict:
    return {
        "plan": {
            "id": "plan_001",
            "user_question": "맥도날드의 역사와 운영 원칙을 조사해줘",
            "research_scope": {
                "target": "McDonald's",
                "target_type": "company",
            },
            "briefing_sections": [
                {
                    "id": "overview",
                    "title": "Overview",
                    "section_type": "overview",
                    "priority": "high",
                }
            ],
            "source_requirements": ["official_doc", "news", "critical_source"],
            "research_assignments": [
                {
                    "agent": "Researcher A",
                    "focus": "official and primary sources",
                    "required_source_types": ["official_doc"],
                },
                {
                    "agent": "Researcher B",
                    "focus": "news and industry context",
                    "required_source_types": ["news"],
                },
                {
                    "agent": "Researcher C",
                    "focus": "risks and criticism",
                    "required_source_types": ["critical_source"],
                },
            ],
        },
        "assumptions": [],
        "missing_inputs": [],
        "handoff_notes": ["Researcher assignments are split by source type."],
    }


def test_planner_agent_creates_plan_and_updates_context(tmp_path: Path):
    agent = PlannerAgent(llm=lambda prompt, model: _planner_payload())
    context = AgentContext(
        run_id="run_001",
        user_question="맥도날드의 역사와 운영 원칙을 조사해줘",
        output_root=tmp_path,
    )

    output = agent.plan(context.user_question, context=context)

    assert isinstance(output, PlannerOutput)
    assert context.get_artifact("plan").id == "plan_001"
    assert context.messages[0].message_type == "handoff"
    assert (tmp_path / "run_001" / "messages.json").exists()


def test_planner_agent_normalizes_rich_planning_payload():
    payload = {
        "user_question": "JB금융그룹에 대해 조사해줘",
        "research_target": {
            "name": "JB금융그룹",
            "alternate_names_to_verify": ["JB Financial Group", "JB금융지주"],
            "target_type": "한국 금융지주회사",
            "region": "대한민국",
            "language": "최종 보고서는 한국어, 필요 시 영문 자료 보조",
            "time_range": {
                "historical_scope": "설립부터 현재까지",
                "recent_scope": "최근 3~5년",
            },
            "expected_depth": "공모전용 중간~심층 수준",
        },
        "final_briefing_shape": [
            {
                "section_id": "S1",
                "title": "JB금융그룹 한눈에 보기",
                "purpose": "공모전용 핵심 포지셔닝 정리",
                "key_questions": ["공식 개요는 무엇인가?"],
                "evidence_needs": ["공식 홈페이지", "IR 자료"],
                "source_priority": ["공식 홈페이지", "DART 공시"],
            },
            {"section_id": "S2", "title": "역사와 성장 경로"},
            {"section_id": "S3", "title": "운영 구조와 사업 포트폴리오"},
            {"section_id": "S4", "title": "최근 방향성·비전·리스크"},
        ],
        "researcher_assignments": [
            {
                "researcher": "Researcher A",
                "lane": "공식·1차 자료 수집",
                "primary_sections_supported": ["S1", "S2", "S3", "S4"],
                "source_types_most_important": ["공식 홈페이지", "DART 공시"],
                "search_queries": ["JB금융그룹 회사소개 비전 연혁"],
            },
            {
                "researcher": "Researcher B",
                "lane": "뉴스·산업분석 수집",
                "source_types_most_important": ["경제지 기사", "산업 분석"],
            },
            {
                "researcher": "Researcher C",
                "lane": "리스크·규제 검토",
                "source_types_most_important": ["금융감독원 제재공시", "비판적 언론"],
            },
        ],
        "assumptions": ["공모전 주제는 아직 특정되지 않았다."],
        "missing_inputs": ["공모전의 정확한 주제"],
        "handoff_notes": ["사실 근거와 분석자의 제안을 구분한다."],
    }
    agent = PlannerAgent(llm=lambda prompt, model: payload)

    output = agent.plan("JB금융그룹에 대해 조사해줘")

    assert output.plan.user_question == "JB금융그룹에 대해 조사해줘"
    assert output.plan.research_scope.target == "JB금융그룹"
    assert output.plan.research_scope.depth == "deep"
    assert output.plan.briefing_sections[0].id == "S1"
    assert output.plan.briefing_sections[2].section_type == "operations"
    assert output.plan.research_assignments[0].agent == "Researcher A"
    assert output.plan.research_assignments[0].search_queries == [
        "JB금융그룹 회사소개 비전 연혁"
    ]
    assert "official_doc" in output.plan.source_requirements
    assert "critical_source" in output.plan.source_requirements


def test_planner_agent_rejects_missing_researcher_assignments():
    payload = _planner_payload()
    payload["plan"]["research_assignments"] = payload["plan"]["research_assignments"][:2]
    agent = PlannerAgent(llm=lambda prompt, model: payload)

    with pytest.raises(ValueError, match="Researcher C"):
        agent.plan("question")
