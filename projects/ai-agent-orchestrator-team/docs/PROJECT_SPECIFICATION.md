# AI Agent Orchestrator with MCP Integration - 프로젝트 기획서

## 👥 팀 담당 영역

각 팀원의 상세한 담당 영역과 개발 가이드는 **[README.md](../README.md)** 를 참조하시기 바랍니다.

### 🟡 최현님 - AO (Agent Orchestrator) 영역
- **AO (Agent Orchestrator)**: LangGraph StateGraph 워크플로우 엔진
- **Agent Tools**: CR (Context Registry) Query/Read, CR Write/Insert, Notion MCP (Model Context Protocol) Tool
- **LLaMA 모델 통합**: 독립 모듈로 요약/분석 기능

### 🟢 이지민님 · 이재범님 - MCP (Model Context Protocol) Server 영역  
- **MCP Server Tools**: 대화 로깅, 추출 도구 (내부 AO (Agent Orchestrator) 호출)
- **CR (Context Registry)**: 대화 로그 및 Notion PM 스냅샷 저장소
- **Webhook Ingest**: Notion 연동 및 변경사항 수신

### 🔵 황중원님 - Backoffice 영역
- **Backoffice UI**: Registry Viewer, Agent Flow Monitor
- **Background Jobs**: Daily Priority @07:00 KST 스케줄링
- **정책 및 접근 제어**: (해커톤 범위 외)

---

## 0) 목표 & 범위 (해커톤)

### 핵심 목표
- 상용 앱(Claude/ChatGPT/Gemini/Cursor) → **MCP Client** → **MCP Server**
- 서버 노출 툴: **`conversation_log`(대화 로깅)**, **`extract`(대화 조회/요약)**
- 두 툴은 내부에서 **AO(Agent Orchestrator)** 를 호출하고, AO는 **LangGraph** 기반 **상태 그래프(StateGraph)** 로 동작
- **Context Registry(CR)** 에 대화/요약/결과를 저장·조회
- **Backoffice(HTML+vanilla JS)**: CR 조회/삭제 + **Daily Digest(07:00 KST)** 잡 관리

### 제외 범위
- 보안/시크릿 관리
- 노션·캘린더 연동
- 외부 웹훅 처리

### 기술적 근거
- LangGraph의 상태 그래프/노드·엣지 모델
- 인터럽트/업데이트 기능
- LangGraph의 **MCP 어댑터**(여러 MCP 서버의 툴/리소스를 LangGraph 툴로 로딩)
- MCP 표준 전송(STDIO/SSE)
- Claude Desktop·Cursor의 로컬 MCP 서버 연결 지원

## 1) 상위 아키텍처

### Client Layer
- **ChatGPT Desktop** / **Claude Desktop/CODE** / **Gemini CLI** / **Cursor** + **공통 MCP Client**
- 로컬 MCP 서버 연결은 각 클라이언트의 가이드에 따라 설정
- 예: Claude Desktop 로컬 서버 연결 가이드 준수

### MCP Server (Python)
- **노출 툴**: `conversation_log`, `extract`
- **내부 컴포넌트**: **AO(LangGraph)**, **CR(간단 저장소)**
- **전송**: 기본 **STDIO**, 필요 시 **SSE/HTTP** 전환 가능(표준 규격)

### Backoffice (HTML + vanilla JS)
- **CR Viewer**: 검색/상세/소프트삭제
- **Job 스케줄 관리**: 07:00 KST 트리거
- **AO 실행 로그 뷰**: 실행 히스토리 및 상태 확인

## 2) 데이터 모델

### 공통 메타데이터
- `id`: 고유 식별자
- `record_type`: `conversation | extract_result | action_log`
- `source`: `cursor | chatgpt | claude | gemini`
- `channel`: 대화 채널/세션 식별자
- `payload`: 레코드 타입별 실제 데이터
- `timestamp`: 생성 시간
- `actor`: `ao | tool | backoffice`
- `deleted`: 소프트 삭제 플래그

### conversation 레코드
- `payload.messages[]`: 메시지 배열 (role/text/ts)
- `tags`: `["raw"]` (기본값)

### extract_result 레코드
- `payload.result_type`: `raw | summary | digest`
- `items[{text, ts}]`: 추출된 결과 아이템들

### action_log 레코드
- `payload.action`: `digest_generated | cleanup`
- `detail{channel, count}`: 액션 상세 정보

## 3) MCP 서버 툴 (I/O 계약)

### `conversation_log` 툴
**입력**:
```json
{
  "channel": "session_id_or_channel_name",
  "messages": [
    {"role": "user", "text": "...", "timestamp": "..."},
    {"role": "assistant", "text": "...", "timestamp": "..."}
  ],
  "meta": {
    "source": "claude|chatgpt|cursor|gemini",
    "additional_info": "..."
  }
}
```

**동작**:
- 내부 AO 호출
- AO가 CR에 `conversation` 저장

**출력**:
```json
{
  "ok": true,
  "stored_ids": ["conv_id_1", "conv_id_2"]
}
```

### `extract` 툴
**입력**:
```json
{
  "channel": "session_id_or_channel_name",
  "query": "search_or_filter_criteria",
  "meta": {
    "source": "claude|chatgpt|cursor|gemini",
    "mode": "raw|summary"
  }
}
```

**동작**:
- AO 호출
- CR에서 해당 채널 최근 대화 조회
- `raw`면 원문 일부 반환
- `summary`면 요약 생성
- CR에 `extract_result` 저장

**출력**:
```json
{
  "ok": true,
  "result_type": "raw|summary",
  "items": [
    {"text": "...", "timestamp": "..."}
  ],
  "cr_id": "extract_result_id"
}
```

## 4) AO 설계 (LangGraph + MCP Connector)

### 4.1 그래프 형태

#### StateGraph 채택
- 노드는 **State → Partial(State)** 형태로 동작
- 상태 키에 리듀서를 지정 가능 (예: messages append)

#### 노드 구성
- **`plan`**: 입력(meta.source/channel/mode) 기반 실행 스텝 결정
- **`cr_read`**: 채널 기준 최근 N개 대화 조회
- **`summarize`**: 요약 생성 (초기엔 규칙/샘플 LLM; 외부 MCP 툴 붙일 때 MCP Connector로 대체 가능)
- **`cr_write`**: 결과 저장 (extract_result/action_log 등)

#### 흐름 예시
- **대화 로깅**: `tool → plan → cr_write(conversation)`
- **추출(raw)**: `tool → plan → cr_read → cr_write(extract_result.raw)`
- **추출(summary)**: `tool → plan → cr_read → summarize → cr_write(extract_result.summary)`
- **Daily Digest(07:00 KST)**: `Backoffice 잡 → AO → 채널별 최근 대화 요약 → extract_result.digest + action_log 기록`

### 4.2 MCP Connector 사용 계획

#### 초기 단계
- 외부 MCP 툴 사용 **비활성**
- 기본 기능으로 프로토타입 구현

#### 확장 단계
- LangGraph의 **MCP 어댑터**로 복수 MCP 서버에서 **툴/리소스 로딩**
- `summarize` 노드나 별도 도메인 노드에서 호출 가능
- 다중 MCP 서버 관리 가능

### 4.3 운영적 고려사항

#### 인터럽트/중단 기능
- LangGraph의 **인터럽트/중단 지점** 기능(v0.4) 활용
- 추후 사용자 확인이 필요한 단계에서 중단/재개 용이
- 해커톤 기본 플로우는 자동 실행

#### 확장성
- 조건부 엣지(라우팅)·툴 호출 에이전트 패턴은 점진 도입
- 현 스코프는 단순 플로우로 시작

## 5) Backoffice (HTML + vanilla JS)

### 주요 기능

#### CR Viewer
- **필터링**: 기간/record_type/source/channel 기준
- **소프트 삭제**: 물리적 삭제 없이 deleted 플래그 설정
- **상세 보기**: JSON 형태로 레코드 상세 정보 표시

#### Background Jobs
- **Daily Digest @07:00 KST**: 스케줄 ON/OFF 설정
- **수동 실행 버튼**: 즉시 AO 호출하여 digest 생성
- **잡 상태 모니터링**: 실행 상태 및 결과 확인

#### AO Run Log (간단)
- **최근 실행 기록**: 실행 시간/스텝/기록 건수
- **실행 상태**: 성공/실패/진행중 상태 표시

### API 엔드포인트 (예시)

#### CR 관리
- `GET /bo/cr`: CR 데이터 조회 (필터링 지원)
- `DELETE /bo/cr?soft=true`: 소프트 삭제

#### 잡 관리
- `GET /bo/jobs/schedule`: 스케줄 설정 조회
- `POST /bo/jobs/schedule`: 스케줄 설정 변경
- `POST /bo/jobs/run?job=daily_digest&channel=...`: 수동 잡 실행

#### 로그 조회
- `GET /bo/ao/logs`: AO 실행 로그 조회

## 6) 개발 작업 순서 (권장)

### Phase 1: 기반 구조
1. **환경 설정**: uv를 사용한 의존성 관리 및 프로젝트 구조
2. **CR 저장소 구현**: 인메모리 저장소(또는 SQLite) & 모델 스키마 정의
3. **AO 최소 구성**: `plan`/`cr_write`/`cr_read`/`summarize(룰기반)` 노드 구현

### Phase 2: 핵심 기능
4. **MCP Server 구현**: `conversation_log`/`extract` 툴 → 내부 AO 호출 연결
5. **Backoffice 기본**: CR 리스트/상세/삭제, Daily Digest 수동 실행 UI → AO 호출 → 결과 확인

### Phase 3: 통합 및 자동화
6. **스케줄러 구현**: 07:00 KST 트리거(간단 크론) → AO 실행 → digest 기록
7. **클라이언트 연결 테스트**: Claude Desktop·Cursor에서 로컬 MCP 서버로 호출

## 7) 수용 기준 (테스트)

### 기능별 테스트 시나리오

#### 대화 로깅 테스트
- **시나리오**: 각 클라이언트에서 `conversation_log` 호출
- **기대 결과**: CR에 `conversation` 생성 (소스/채널/타임스탬프 포함)

#### 추출 기능 테스트
- **시나리오**: 지정 채널 기준 원문/요약 요청
- **기대 결과**: 원문/요약 결과 반환 및 CR에 `extract_result` 기록

#### Daily Digest 테스트
- **시나리오**: 07:00 KST(또는 수동 실행) 트리거
- **기대 결과**: 채널별 요약(`digest`) + `action_log` 기록

#### Backoffice 테스트
- **시나리오**: 목록 필터·상세·소프트 삭제 및 잡 실행
- **기대 결과**: 모든 UI 기능이 정상 동작

## 8) 향후 확장 포인트 (해커톤 이후)

### 기술적 확장

#### 외부 MCP 툴 통합
- **LangGraph MCP 어댑터**로 도메인 기능 증설
- 다양한 외부 서비스와의 연동 가능

#### 전송 프로토콜 확장
- **HTTP+SSE 전환**: 원격/브라우저 클라이언트 대응
- **재연결 지원**: Last-Event-ID 활용

#### 고급 워크플로우
- **조건부 라우팅**: 복잡한 의사결정 로직
- **다중 단계 계획**: LangGraph 고급 기능 활용

### 클라이언트 확장

#### 설치 가이드 개발
- **Claude Desktop 확장**: 설치/로컬 서버 연결 가이드
- **Cursor MCP Directory**: 활용 방법 문서화

#### 추가 플랫폼 지원
- 새로운 AI 클라이언트 플랫폼 지원
- 브라우저 기반 클라이언트 개발

---

## 부록: 작업 체크리스트

필요시 **작업 체크리스트(이슈/담당/완료 기준)** 를 별도 문서로 제공할 수 있습니다.

### 주요 마일스톤
- [ ] **M1**: 기반 구조 완성 (CR + AO 기본)
- [ ] **M2**: MCP 서버 및 툴 구현
- [ ] **M3**: Backoffice UI 완성
- [ ] **M4**: 클라이언트 연동 테스트
- [ ] **M5**: 스케줄러 및 자동화 완성

### 성공 지표
- 모든 지원 클라이언트에서 MCP 툴 호출 성공
- Daily Digest 자동 생성 및 스케줄링 동작
- Backoffice를 통한 데이터 관리 및 모니터링 가능