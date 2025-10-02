# 팀 협업 가이드

## 🎯 해커톤 데모 개요

이 프로젝트는 MCP(Model Context Protocol) 통합을 포함한 AI Agent Orchestrator를 시연합니다:

- **MCP Server**: AI 클라이언트 통신을 위한 프로토콜 레이어
- **Agent Orchestrator**: LangGraph 기반 워크플로우 엔진  
- **Context Registry**: 대화 및 결과를 위한 SQLite 저장소
- **Backoffice UI**: 데이터 관리를 위한 웹 인터페이스

## 👥 팀 구조 및 담당 영역

### 🟡 이재범님 - AO (Agent Orchestrator) 영역
**담당**: LangGraph 기반 에이전트 오케스트레이션 
- **AO (Agent Orchestrator)** (`agent_orchestrator/`)
  - 계획/플래너 로직 구현
  - StateGraph 워크플로우 설계
- **Agent Tools** 구현
  - CR (Context Registry) Query/Read 도구
  - CR (Context Registry) Write/Insert 도구  
  - Notion MCP (Model Context Protocol) Tool (write/search)
- **LLaMA 모델 통합** (독립 모듈)

### 🟢 이지민님 · 최현님 - MCP (Model Context Protocol) Server 영역  
**담당**: MCP 프로토콜 및 도구 구현
- **MCP Server Tools** (`mcp_server/`)
  - Tool: 대화 로깅 (내부에서 AO (Agent Orchestrator) 호출)
  - Tool: 추출 (내부에서 AO (Agent Orchestrator) 호출)
- **CR (Context Registry)** (`context_registry/`)
  - 대화 로그 저장소
  - Notion PM 스냅샷 관리
- **Webhook Ingest** (Notion 연동)

### 🔵 황중원님 - Backoffice 영역
**담당**: 관리 인터페이스 및 모니터링
- **Backoffice UI** (`backoffice/`)
  - Registry Viewer & Trace (CR (Context Registry) 직접 조회/삭제)
  - Agent Flow Monitor
- **Background Jobs 관리**
  - Daily Priority @07:00 KST (조건·대상 설정, AO (Agent Orchestrator) 호출)
  - 스케줄링 및 잡 관리 UI
- **정책 및 접근 제어** (해커톤 범위 외)

## 🚀 빠른 시작

### 1. 환경 설정
```bash
# 클론 및 설정
git clone <repository>
cd ai-prompt-history-llama
git checkout feature/hackathon-demo-mockup

# uv 설치 (아직 설치하지 않았다면)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 의존성 설치
uv sync
```

### 2. 데모 시작
```bash
# 모든 컴포넌트 시작
uv run python start_demo.py

# 또는 개별 시작:
uv run python context_registry/registry.py &
uv run python agent_orchestrator/orchestrator.py &
uv run python mcp_server/server.py &
uv run python backoffice/app.py &
```

### 3. 접속 포인트
- **Backoffice UI**: http://localhost:8003
- **MCP (Model Context Protocol) Server**: stdio/HTTP 클라이언트 연결용
- **AO (Agent Orchestrator)**: 포트 8001 (내부용)
- **CR (Context Registry)**: 포트 8002 (내부용)

## 🔧 개발 워크플로우

### 🟡 이재범님 작업 영역

#### Agent Orchestrator (`agent_orchestrator/orchestrator.py`)
```python
# StateGraph 워크플로우 구현:
def _create_graph(self):
    workflow = StateGraph(AgentState)
    workflow.add_node("plan", self._plan_node)      # 계획/플래너 로직
    workflow.add_node("cr_read", self._cr_read_node) 
    workflow.add_node("summarize", self._summarize_node)
    workflow.add_node("cr_write", self._cr_write_node)
```

#### Agent Tools 구현
```python
# CR (Context Registry) Query/Read 도구
async def cr_query(self, filters: Dict) -> List[Record]:
    # CR (Context Registry) 조회 로직

# CR (Context Registry) Write/Insert 도구  
async def cr_write(self, data: Record) -> str:
    # CR (Context Registry) 저장 로직

# Notion MCP (Model Context Protocol) Tool
async def notion_tool(self, action: str, data: Dict) -> Dict:
    # Notion write/search 기능
```

#### LLaMA 모델 통합
- 독립 모듈로 구현
- AO (Agent Orchestrator)에서 요약/분석 시 호출
- 로컬 LLaMA 3.2 모델 활용

### 🟢 이지민님 · 최현님 작업 영역

#### MCP Server Tools (`mcp_server/server.py`)
```python
# 대화 로깅 툴 (내부에서 AO (Agent Orchestrator) 호출)
@mcp.tool("conversation_log", description="...")
async def conversation_log(...):
    # AO (Agent Orchestrator) 호출 로직
    result = await orchestrator.process_conversation(data)

# 추출 툴 (내부에서 AO (Agent Orchestrator) 호출)
@mcp.tool("extract", description="...")  
async def extract(...):
    # AO (Agent Orchestrator) 호출 로직
    result = await orchestrator.process_extraction(data)
```

#### Context Registry (`context_registry/registry.py`)
```python
# 데이터 모델 확장:
@dataclass
class ConversationRecord: ...      # 대화 로그
@dataclass 
class ExtractResultRecord: ...     # 추출 결과
@dataclass
class NotionSnapshotRecord: ...    # Notion PM 스냅샷
```

#### Webhook Ingest (Notion 연동)
- Notion 변경사항 수신
- PM 스냅샷 저장
- CR (Context Registry)에 데이터 저장

### 🔵 황중원님 작업 영역

#### Backoffice UI (`backoffice/app.py`)
```python
# Registry Viewer & Trace
@app.get("/cr/view")
async def view_registry():
    # CR (Context Registry) 직접 조회/삭제 인터페이스

# Agent Flow Monitor  
@app.get("/agent/monitor")
async def monitor_agent():
    # AO (Agent Orchestrator) 실행 상태 모니터링
```

#### Background Jobs 관리
```python
# Daily Priority Job
@app.post("/jobs/daily-priority")
async def trigger_daily_priority():
    # 07:00 KST 스케줄링
    # 조건·대상 설정
    # AO (Agent Orchestrator) 호출 로직
```

#### 템플릿 개발 (`backoffice/templates/`)
- `registry.html`: CR (Context Registry) 뷰어 및 트레이스
- `monitor.html`: Agent Flow 모니터
- `jobs.html`: Background Jobs 관리
- `dashboard.html`: 통합 대시보드

## 📊 데이터 플로우 테스트

### 1. 대화 플로우 테스트
```bash
# MCP (Model Context Protocol) 클라이언트를 통해:
conversation_log(
    session_id="test_001",
    user_message="안녕하세요",
    assistant_response="안녕하세요!",
    platform="claude"
)
```

### 2. 추출 플로우 테스트  
```bash
# MCP (Model Context Protocol) 클라이언트를 통해:
extract(
    content="회의 노트와 액션 아이템...",
    extract_type="action_items"
)
```

### 3. Backoffice에서 확인
- http://localhost:8003/conversations 확인
- http://localhost:8003/extracts 검토
- http://localhost:8003/jobs 모니터링

## 🎪 데모 준비

### 데모 스크립트
1. **시스템 시작**: `python start_demo.py`
2. **아키텍처 설명**: 3레이어 설계 설명
3. **MCP 툴 테스트**: conversation_log와 extract 사용
4. **결과 브라우징**: backoffice UI 탐색
5. **잡 트리거**: daily digest 수동 실행

### 주요 데모 포인트
- **MCP 프로토콜**: 클라이언트 독립적 통신
- **LangGraph 워크플로우**: 4노드 상태 머신
- **영구 저장소**: 구조화된 데이터가 있는 SQLite
- **실시간 UI**: 라이브 데이터 조회 및 관리

## 🔍 디버깅

### 컴포넌트 로그
```bash
# 개별 컴포넌트 로그 확인
tail -f context_registry.log
tail -f agent_orchestrator.log  
tail -f mcp_server.log
tail -f backoffice.log
```

### 일반적인 문제
1. **포트 충돌**: 8001, 8002, 8003 확인
2. **데이터베이스 락**: Context Registry 재시작
3. **MCP 연결**: 클라이언트 설정 검증
4. **모듈 임포트**: PYTHONPATH 설정 확인

## 📝 코드 표준

### Python 스타일
- 모든 함수에 타입 힌트 사용
- 공개 메서드에 docstring 추가
- async/await 패턴 준수
- 예외 처리를 우아하게 처리

### 데이터베이스 작업
- 다중 테이블 업데이트에 트랜잭션 사용
- 쿼리를 위한 적절한 인덱싱 추가
- 모든 중요한 작업 로깅
- 저장 전 데이터 검증

### API 설계
- backoffice를 위한 RESTful 엔드포인트
- 일관된 JSON 응답 형식
- 적절한 HTTP 상태 코드
- 입력 검증 및 새니타이징

## 🎁 확장 아이디어

### 고급 팀용
1. **실시간 업데이트**: WebSocket 통합
2. **고급 분석**: 대화 인사이트
3. **내보내기 기능**: 데이터 내보내기 도구
4. **인증**: 사용자 관리 시스템
5. **모니터링**: 헬스 체크 대시보드

### 성능 최적화
1. **데이터베이스 인덱싱**: 쿼리 최적화
2. **캐싱 레이어**: Redis 통합
3. **비동기 처리**: 백그라운드 잡 큐
4. **연결 풀링**: 데이터베이스 연결

## 📞 지원

### 팀 커뮤니케이션
- **🟡 이재범님**: AO (Agent Orchestrator) 핵심 로직 및 LLaMA 통합
- **🟢 이지민님 · 최현님**: MCP (Model Context Protocol) Server 및 CR (Context Registry) 구현  
- **🔵 황중원님**: Backoffice UI 및 모니터링 시스템
- **데모 코디네이터**: 전체 시스템 통합 및 프레젠테이션 준비

### 리소스
- 프로젝트 README: 아키텍처 개요
- API 문서: 엔드포인트 명세
- 컴포넌트 README: 개별 서비스 가이드
- 데모 스크립트: 테스트 절차