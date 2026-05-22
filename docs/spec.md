# 출처 기반 단순 자료조사용 멀티 에이전트 시스템 명세

## 1. 시스템 목표

이 시스템은 사용자가 특정 기업, 기관, 인물, 제품, 산업, 기술, 사건 등에 대해 빠르게 신뢰할 만한 배경 정보를 파악하도록 돕는 출처 기반 자료조사 시스템이다.

예를 들어 "맥도날드라는 기업의 역사, 운영 원칙, 방향성 등에 대해 알려줘" 같은 질문에 대해 공식 자료, 연차보고서, 언론 보도, 업계 분석, 참고 자료를 모아 구조화된 브리핑을 작성한다.

이 시스템은 논쟁형 검토나 찬반 판정을 위한 시스템이 아니다. 핵심은 주제의 배경, 흐름, 주요 특징, 운영 방식, 현재 방향성을 출처와 함께 정리하는 것이다.

핵심 목표는 다음과 같다.

- **조사 범위 구조화**: 사용자 질문을 역사, 조직, 운영 방식, 전략, 최근 동향 등 조사 섹션으로 나눈다.
- **출처 기반 자료 수집**: 공식 자료, 원문 문서, 보고서, 언론, 업계 분석 등 다양한 자료를 찾는다.
- **관점 다양성 확보**: 공식 설명뿐 아니라 외부 분석과 비판적 시각도 함께 확인한다.
- **기본 사실 확인**: 날짜, 인물, 조직명, 수치처럼 틀리기 쉬운 정보를 출처 간 대조한다.
- **누락 점검**: 조사 결과에서 중요한 시기, 사업 영역, 지역, 관점, 자료 유형이 빠졌는지 확인한다.
- **간결한 브리핑 작성**: 사용자가 바로 읽을 수 있는 구조화된 보고서를 만든다.

비목표는 다음과 같다.

- 모든 문장을 세부 근거 단위로 엄밀하게 추적하지 않는다.
- 찬반 판정이나 반박 보고서 작성을 기본 목적으로 삼지 않는다.
- 학술적 체계적 문헌고찰이나 메타분석을 대체하지 않는다.
- 법률, 의료, 금융 등 고위험 의사결정에 대한 최종 판단을 제공하지 않는다.
- 사용자의 선호 결론에 맞춰 편향된 자료만 고르지 않는다.

## 2. 에이전트 역할

### 2.1 Planner Agent

조사 전체의 목차와 실행 계획을 만든다.

- 사용자 질문에서 조사 대상과 원하는 정보 범위를 파악한다.
- 조사 섹션을 만든다. 예: 역사, 창업자, 비즈니스 모델, 운영 원칙, 조직 문화, 전략 방향, 최근 동향, 논란 또는 리스크.
- 필요한 출처 유형을 정의한다.
- 각 Researcher Agent가 서로 다른 자료군과 관점으로 조사하도록 작업을 배정한다.
- 질문이 너무 넓으면 우선순위를 정한다.

Planner는 다음을 산출한다.

- `research_scope`: 조사 대상과 범위
- `briefing_sections`: 최종 보고서에 들어갈 섹션
- `source_requirements`: 필요한 출처 유형
- `research_assignments`: Researcher별 조사 과제

### 2.2 Researcher Agents

서로 다른 자료군, 검색어, 관점으로 독립 조사한다. 기본 MVP에서는 Researcher A, B, C 세 명을 사용한다.

- **Researcher A**: 공식 자료, 회사 웹사이트, 연차보고서, 보도자료, 원문 문서를 우선 조사한다.
- **Researcher B**: 언론 보도, 업계 분석, 시장 보고서, 전문가 해설을 중심으로 조사한다.
- **Researcher C**: 비판적 관점, 논란, 리스크, 노동·환경·규제 이슈, 외부 평가를 찾는다.

각 Researcher는 다음 원칙을 따른다.

- 자료에서 확인한 내용을 섹션별로 정리한다.
- 반드시 출처 URL, 발행자, 발행일 또는 접근일을 포함한다.
- 출처가 약하거나 확인이 어려운 내용은 그렇게 표시한다.
- 모르는 것은 추정하지 않고 `unknown` 또는 `not_found`로 표시한다.
- 다른 Researcher와 일부 중복될 수 있지만, 자료군과 검색 전략은 달라야 한다.

### 2.3 Critic Agent

Researcher들의 결과를 품질 관점에서 검토한다.

- 특정 출처 유형에 치우쳤는지 확인한다.
- 공식 자료의 자기홍보성, 언론 자료의 단편성, 블로그 자료의 신뢰도 문제를 표시한다.
- 빠진 시기, 빠진 지역, 빠진 사업 영역, 빠진 비판적 관점이 있는지 점검한다.
- 서로 다른 자료 사이의 날짜, 수치, 명칭 불일치를 찾는다.
- 최종 브리핑에 단정적으로 쓰기 어려운 내용을 표시한다.

Critic은 결론을 직접 작성하지 않는다. 조사 품질의 약점과 보완 필요 사항을 Verifier와 Synthesizer에게 넘긴다.

### 2.4 Verifier Agent

브리핑에 들어갈 기본 사실과 출처 일관성을 확인한다.

- 창립연도, 창업자, 본사, 주요 사건 연표, CEO, 매출, 매장 수 같은 기본 사실을 대조한다.
- 최신성이 중요한 정보는 발행일과 접근일을 확인한다.
- 출처 간 내용이 충돌하면 어떤 항목이 충돌하는지 표시한다.
- 확인이 부족한 항목은 `needs_care`로 표시한다.
- 논쟁적 판단 대신 브리핑에서 조심해서 표현해야 할 사실을 알려준다.

검토 라벨 기준은 다음과 같다.

- `confirmed`: 신뢰할 만한 출처로 기본 사실이 확인됨
- `needs_care`: 출처가 부족하거나 최신성, 맥락, 표현에 주의가 필요함
- `conflicting`: 출처 간 정보가 서로 충돌함

### 2.5 Synthesizer Agent

조사 결과를 바탕으로 최종 브리핑 보고서를 작성한다.

- 사용자 질문에 맞는 목차로 내용을 정리한다.
- 공식 설명, 외부 분석, 비판적 관점을 구분해 균형 있게 반영한다.
- 확인이 부족한 정보는 단정하지 않고 조심스럽게 표현한다.
- 핵심 연표, 운영 원칙, 비즈니스 모델, 방향성, 리스크를 읽기 쉽게 요약한다.
- 출처 목록과 주요 참고 자료를 포함한다.

## 3. 전체 워크플로

1. **질문 입력**
   - 사용자가 조사할 대상을 입력한다.
   - 필요한 경우 지역, 기간, 깊이, 선호 자료 유형을 받는다.

2. **조사 계획 수립**
   - Planner Agent가 조사 범위와 브리핑 섹션을 정한다.
   - 필요한 출처 유형과 Researcher별 조사 전략을 정의한다.

3. **병렬 자료 조사**
   - Researcher A/B/C가 각자 다른 자료군과 검색어로 조사한다.
   - 각 결과는 출처, 핵심 내용, 한계, 확인하지 못한 점을 포함해야 한다.

4. **품질 점검**
   - Critic Agent가 자료 편향, 누락, 신뢰도 문제, 불일치를 점검한다.
   - 보완이 필요한 항목을 표시한다.

5. **기본 사실 확인**
   - Verifier Agent가 브리핑에 들어갈 핵심 사실을 출처 간 대조한다.
   - 각 항목을 `confirmed`, `needs_care`, `conflicting`으로 표시한다.

6. **최종 브리핑 작성**
   - Synthesizer Agent가 사용자가 읽기 쉬운 보고서를 작성한다.
   - 확인이 부족하거나 충돌하는 내용은 별도 주의 표시를 붙인다.

7. **결과 저장**
   - 조사 계획, 자료 메모, 품질 점검, 사실 확인 결과, 최종 브리핑을 저장한다.
   - 이후 같은 대상의 업데이트 조사에 재사용한다.

## 4. 데이터 스키마

아래 스키마는 MVP에서 사용할 논리 구조다. 모든 정보를 영구 DB에 반드시 저장할 필요는 없지만, 에이전트 간 전달 형식은 이 구조를 따른다.

### 4.1 Research Plan

```json
{
  "id": "plan_001",
  "user_question": "맥도날드라는 기업의 역사, 운영 원칙, 방향성 등에 대해 알려줘",
  "research_scope": {
    "target": "McDonald's Corporation",
    "target_type": "company",
    "time_range": "founding_to_present",
    "region": "global",
    "language": ["ko", "en"],
    "depth": "standard"
  },
  "briefing_sections": [
    {
      "id": "section_001",
      "title": "기업 개요",
      "priority": "high"
    },
    {
      "id": "section_002",
      "title": "역사와 주요 전환점",
      "priority": "high"
    },
    {
      "id": "section_003",
      "title": "운영 원칙과 비즈니스 모델",
      "priority": "high"
    }
  ],
  "source_requirements": [
    "official_doc",
    "annual_report",
    "news",
    "industry_analysis",
    "critical_source"
  ],
  "research_assignments": [
    {
      "agent": "Researcher A",
      "focus": "공식 자료와 원문 문서",
      "required_source_types": ["official_doc", "annual_report", "press_release"]
    }
  ],
  "created_at": "2026-05-22T00:00:00Z"
}
```

### 4.2 Source

```json
{
  "id": "source_001",
  "title": "자료 제목",
  "url": "https://example.org/report",
  "publisher": "Example Publisher",
  "author": "Author Name",
  "published_at": "2025-09-01",
  "accessed_at": "2026-05-22",
  "source_type": "annual_report",
  "reliability": "high",
  "relevance": "high",
  "notes": "회사 원문 자료이며 재무와 전략 설명을 포함한다."
}
```

필드 설명:

- `source_type`: `official_doc`, `annual_report`, `press_release`, `primary_source`, `news`, `industry_analysis`, `paper`, `book`, `reference`, `blog`, `social_media`, `critical_source`, `other`
- `reliability`: `high`, `medium`, `low`, `unknown`
- `relevance`: `high`, `medium`, `low`

### 4.3 Research Note

```json
{
  "id": "note_001",
  "researcher": "Researcher A",
  "section_id": "section_002",
  "topic": "역사와 주요 전환점",
  "summary": "자료에서 확인한 핵심 내용 요약",
  "source_ids": ["source_001"],
  "confidence": "medium",
  "limitations": [
    "회사 공식 설명이므로 비판적 관점은 부족하다."
  ],
  "unknowns": [
    "일부 지역별 운영 변화는 확인하지 못했다."
  ]
}
```

필드 설명:

- `confidence`: Researcher의 1차 신뢰 판단이며 최종 사실 확인 라벨이 아니다.
- `limitations`: 자료 또는 조사 범위의 한계
- `unknowns`: 찾지 못했거나 확인하지 못한 부분

### 4.4 Quality Review

```json
{
  "id": "review_001",
  "target_note_id": "note_001",
  "issues": [
    {
      "type": "source_bias",
      "severity": "medium",
      "description": "공식 자료에 의존해 회사의 자기 설명이 강하게 반영될 수 있다."
    },
    {
      "type": "missing_context",
      "severity": "medium",
      "description": "프랜차이즈 운영의 노동 이슈와 지역별 차이가 충분히 다뤄지지 않았다."
    }
  ],
  "suggested_checks": [
    "외부 업계 분석 자료 추가 확인",
    "최근 언론 보도와 규제 이슈 확인"
  ]
}
```

필드 설명:

- `type`: `source_bias`, `source_quality`, `staleness`, `missing_context`, `inconsistency`, `overgeneralization`, `other`
- `severity`: `low`, `medium`, `high`

### 4.5 Fact Check

```json
{
  "id": "fact_001",
  "item": "창립연도",
  "value": "1955",
  "status": "confirmed",
  "rationale": "회사 공식 자료와 복수의 참고 자료가 같은 연도를 제시한다.",
  "source_ids": ["source_001", "source_002"],
  "notes": "맥도날드 형제가 운영한 초기 레스토랑과 Ray Kroc의 법인 설립 시점을 구분해 표현해야 한다."
}
```

필드 설명:

- `status`: `confirmed`, `needs_care`, `conflicting`
- `rationale`: 왜 이 라벨을 붙였는지에 대한 짧은 설명
- `notes`: 표현상 주의할 점

### 4.6 Final Briefing

```json
{
  "id": "briefing_001",
  "title": "맥도날드 기업 브리핑",
  "user_question": "맥도날드라는 기업의 역사, 운영 원칙, 방향성 등에 대해 알려줘",
  "executive_summary": "현재 조사 결과의 핵심 요약",
  "sections": [
    {
      "heading": "기업 개요",
      "content": "조사 내용을 바탕으로 작성한 본문",
      "source_ids": ["source_001"]
    }
  ],
  "timeline": [
    {
      "year": "1955",
      "event": "Ray Kroc이 McDonald's System, Inc.를 설립",
      "source_ids": ["source_001"]
    }
  ],
  "key_points": [
    "프랜차이즈 모델이 글로벌 확장의 핵심이었다."
  ],
  "care_points": [
    "초기 역사에서는 맥도날드 형제의 레스토랑과 Ray Kroc의 법인화를 구분해야 한다."
  ],
  "source_list": ["source_001", "source_002"],
  "method_notes": "Researcher A/B/C가 공식 자료, 외부 분석, 비판적 자료를 나눠 조사했고 Critic과 Verifier가 누락과 기본 사실을 점검했다.",
  "created_at": "2026-05-22T00:00:00Z"
}
```

## 5. MVP 범위

MVP는 단일 주제에 대해 출처 기반 자료조사를 수행하고 구조화된 브리핑을 생성하는 최소 기능을 목표로 한다.

### 포함 범위

- 단일 사용자 질문 입력
- Planner의 조사 범위와 브리핑 섹션 생성
- Researcher A/B/C의 병렬 자료 조사
- 출처 URL, 발행자, 발행일 또는 접근일 기록
- Researcher별 자료 요약, 한계, unknowns 기록
- Critic의 자료 편향, 누락, 신뢰도 문제 점검
- Verifier의 기본 사실 확인과 주의 항목 표시
- Synthesizer의 최종 Markdown 브리핑 생성
- 출처 목록과 주요 참고 자료 포함

### 제외 범위

- 모든 문장 단위 citation 관리
- 찬반 판정이나 반박 중심 워크플로
- 장기 지식 그래프 구축
- 자동 인용 스타일 변환
- 전체 논문 품질 평가 자동화
- 팀 협업 기능
- 고위험 전문 분야의 최종 의사결정

### MVP 품질 기준

- 최소 4개 이상의 브리핑 섹션을 제시한다.
- 최소 3개 이상의 서로 다른 출처 유형을 사용한다.
- 공식 자료와 외부 자료를 모두 포함한다.
- Researcher별 조사 결과에는 반드시 출처와 한계가 포함된다.
- Critic은 최소 1개 이상의 누락 또는 편향 가능성을 기록한다.
- Verifier는 핵심 기본 사실을 최소 5개 이상 확인한다.
- 최종 브리핑에는 개요, 주요 연표, 운영 방식 또는 구조, 현재 방향성, 주의할 점, 출처 목록이 포함된다.

## 6. 나중에 추가할 기능

### 6.1 조사 품질 고도화

- 대상 유형별 Planner 템플릿: 기업, 인물, 제품, 산업, 기술, 사건
- 분야별 신뢰 출처 우선순위
- 출처 신뢰도 자동 점수화
- 오래된 자료 자동 경고
- 원문 접근 가능 여부 확인
- 지역별 자료 균형 점검

### 6.2 브리핑 기능 고도화

- 기업용 섹션 템플릿: 역사, 사업 모델, 재무, 제품, 조직 문화, 전략, 리스크
- 인물용 섹션 템플릿: 생애, 경력, 주요 업적, 논란, 영향
- 산업용 섹션 템플릿: 시장 구조, 주요 기업, 가치사슬, 규제, 트렌드
- 수치 정보 전용 최신성 점검
- 연표 자동 생성
- 용어 사전 자동 생성

### 6.3 출력 및 연동

- PDF, HTML, DOCX 내보내기
- JSON 형태의 조사 결과 export
- Notion, Obsidian, Google Docs 연동
- 출처별 citation export
- 업데이트 조사를 위한 저장 쿼리 생성

### 6.4 운영 기능

- 조사 깊이 프리셋: quick, standard, deep
- Researcher 수 조절
- 언어와 지역 범위 설정
- 비용과 시간 예산 관리
- 에이전트별 실행 로그 확인
