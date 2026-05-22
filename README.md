# Research System 사용법

출처 기반 자료조사 리포트를 만드는 작은 CLI 도구입니다.

예를 들어 `"a"`라는 주제로 자료조사 리포트를 받고 싶으면, 아래 순서대로 실행하면 됩니다.

## 1. 준비

프로젝트 폴더에서 실행합니다.

```powershell
cd C:\research_system
```

필요한 패키지를 설치합니다.

```powershell
python -m pip install -e .
```

OpenAI API 키를 설정합니다.

```powershell
$env:OPENAI_API_KEY="sk-..."
```

기본 LLM 설정은 다음과 같습니다.

```text
model: gpt-5.5
reasoning effort: high
verbosity: high
```

다른 모델을 쓰고 싶으면 이렇게 바꿀 수 있습니다.

```powershell
$env:RESEARCH_SYSTEM_OPENAI_MODEL="gpt-5.2"
```

## 2. 자료조사 실행

`"a"`라는 주제로 조사하려면:

```powershell
python -m research_system.cli --run-id a_report "a"
```

조금 더 구체적으로 쓰는 것이 보통 더 좋습니다.

```powershell
python -m research_system.cli --run-id a_report "a에 대해 개요, 역사, 운영 구조, 최근 방향성, 주의할 점을 조사해줘"
```

## 3. 결과 확인

실행이 끝나면 결과는 아래 폴더에 저장됩니다.

```text
outputs\a_report\
```

가장 먼저 볼 파일은 이것입니다.

```text
outputs\a_report\briefing.md
```

함께 생성되는 주요 파일:

```text
plan.json              조사 계획
research_results.json  Researcher A/B/C 조사 결과
critic.json            품질 검토 결과
verifier.json          사실 검증 결과
briefing.json          최종 리포트 JSON
briefing.md            최종 리포트 Markdown
messages.json          에이전트 간 메시지
context.json           전체 실행 스냅샷
```

## 4. 매번 다른 주제로 실행하기

`--run-id`와 마지막 질문만 바꾸면 됩니다.

```powershell
python -m research_system.cli --run-id samsung_report "삼성전자의 최근 사업 방향과 리스크를 조사해줘"
```

```powershell
python -m research_system.cli --run-id openai_report "OpenAI의 제품 구조, 경쟁 환경, 주요 리스크를 조사해줘"
```

## 5. 알아둘 점

현재 CLI 기본 실행은 OpenAI LLM을 사용합니다.

실제 웹 검색 backend는 아직 CLI에 직접 연결되어 있지 않으므로, 최신 자료를 강하게 요구하는 리포트에서는 품질 게이트가 실패할 수 있습니다. 실패하면 에러 메시지에 부족한 항목이 나옵니다.

자주 보는 에러:

```text
No LLM client configured
```

해결:

```powershell
$env:OPENAI_API_KEY="sk-..."
```

모델 접근 권한이 없다는 에러가 나오면:

```powershell
$env:RESEARCH_SYSTEM_OPENAI_MODEL="접근 가능한 모델명"
```

그 다음 다시 실행하면 됩니다.
