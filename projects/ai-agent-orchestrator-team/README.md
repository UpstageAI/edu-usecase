# AI Agent Orchestrator with Context Registry

---

## 팀원 소개

**팀명**: AI Agent Orchestrator Team (5명)  
**교육 프로그램**: Meta x Llama Academy 최종 프로젝트 (2025년 9월 30일 ~ 10월 2일)

### 팀원 및 역할
- **배승환님 : 기획자 역할 담당
  - 발표 문서 작성 및 발표

- **최현님 (🟡)**: AO (Agent Orchestrator) 영역 담당
  - LangGraph StateGraph 워크플로우 엔진 구현
  - Agent Tools (CR Query/Read, CR Write/Insert, Notion MCP Tool) 개발
  - LLaMA 모델 통합 (독립 모듈로 요약/분석 기능)

- **이지민님 · 이재범님 (🟢)**: MCP Server 영역 담당
  - MCP Server Tools 구현 (대화 로깅, 추출 도구)
  - Context Registry (CR) 구현 및 관리
  - Webhook Ingest 및 Notion 연동

- **황중원님 (🔵)**: Backoffice 영역 담당
  - Backoffice UI 개발 (Registry Viewer, Agent Flow Monitor)
  - Background Jobs 구현 (Daily Priority @07:00 KST)
  - 정책 및 접근 제어 설계

---

## 프로젝트 개요

본 프로젝트는 **MCP (Model Context Protocol)**와 **LangGraph**를 활용한 AI 에이전트 오케스트레이션 시스템입니다. 

여러 AI 클라이언트(ChatGPT Desktop, Claude Desktop/CODE, Cursor 등)에서 발생하는 대화 데이터를 수집·저장·분석하고, 이를 바탕으로 지능적인 인사이트를 제공하는 통합 플랫폼으로 설계되었습니다.

### 프로젝트 목표
- MCP 프로토콜을 통한 다중 AI 클라이언트 통합
- LangGraph 기반의 에이전트 워크플로우 구현
- 대화 컨텍스트의 영구 저장 및 효율적 검색
- 자동화된 일일 브리핑 및 인사이트 생성
- 웹 기반 관리 인터페이스 제공

---

## 주요 기능

### 1. **다중 AI 클라이언트 지원**
- ChatGPT Desktop, Claude Desktop/CODE, Gemini CLI, Cursor, Notion 등 다양한 AI 플랫폼 연동
- MCP 프로토콜을 통한 표준화된 통신 인터페이스

### 2. **실시간 대화 로깅 및 추출**
- `conversation_log`: 대화 데이터를 Context Registry에 자동 기록
- `extract`: 대화에서 핵심 정보 및 인사이트 추출

### 3. **Agent Orchestrator (LangGraph 기반)**
- **plan**: 요청 분석 및 처리 전략 수립
- **cr_read**: Context Registry에서 관련 컨텍스트 검색
- **summarize**: 대화 내용 요약 및 처리
- **cr_write**: 결과를 Context Registry에 저장

### 4. **Context Registry (영구 저장소)**
- SQLite 기반의 경량 데이터베이스
- 3개 주요 테이블:
  - `conversation`: 대화 메타데이터 및 내용 저장
  - `extract_result`: 추출된 결과 저장
  - `action_log`: 시스템 액션 및 작업 추적

### 5. **Backoffice 웹 인터페이스**
- Context Registry 데이터 조회 및 관리
- Background Job 스케줄링 및 모니터링
- 작업 실행 히스토리 추적
- 대시보드 및 통계 제공

### 6. **Daily Briefing (일일 브리핑)**
- 매일 자동 실행 (기본: 07:00 KST)
- Gmail, Slack, Notion 등 다중 소스 통합
- AI 기반 내용 분석 및 요약
- Notion 페이지에 자동 게시
- 웹 UI에서 수동 실행 및 결과 확인 가능

### 7. **MCP 통합**
- **Gmail**: 이메일 검색 및 읽기
- **Notion**: 페이지 조회 및 업데이트
- **Slack**: 메시지 조회 (계획 중)

---

## 기술 스택 및 아키텍처

### 기술 스택

#### **Backend**
- **Python 3.10+**: 주요 개발 언어
- **FastAPI**: 웹 API 프레임워크
- **LangGraph**: 에이전트 워크플로우 엔진
- **SQLite**: 경량 데이터베이스
- **MCP (Model Context Protocol)**: AI 클라이언트 통신 표준

#### **AI & ML**
- **LLaMA 3.2**: 로컬 LLM 실행 (Meta Llama Academy 과제용)
- **Upstage Solar**: 한국어 최적화 LLM API (OpenAI 호환)
- **OpenAI API**: 범용 LLM 옵션
- **Hugging Face Transformers**: 모델 로딩 및 추론

#### **Frontend**
- **Jinja2**: 템플릿 엔진
- **HTML/CSS/JavaScript**: Backoffice UI

#### **DevOps & Tools**
- **uv**: Python 패키지 관리자
- **APScheduler**: 백그라운드 작업 스케줄링
- **aiohttp**: 비동기 HTTP 클라이언트

### 아키텍처

```mermaid
flowchart LR
  %% ==== Styles ====
  classDef ownerJB fill:#fde68a,stroke:#b45309,color:#7c2d12
  classDef ownerJMCH fill:#bbf7d0,stroke:#166534,color:#064e3b
  classDef ownerHJW fill:#c7d2fe,stroke:#3730a3,color:#1e3a8a
  classDef neutral fill:#e5e7eb,stroke:#6b7280,color:#374151

  %% ===== Client Layer =====
  subgraph "Client Layer"
    direction TB
    subgraph "Commercial Apps"
      T1["ChatGPT Desktop"]
      T2["Claude Desktop/CODE"]
      T3["Cursor"]
      T4["Notion"]
    end
    C0["MCP Client"]
  end
  class T1,T2,T3,T4,C0 neutral

  T1 --- C0
  T2 --- C0
  T3 --- C0

  %% ===== MCP Server =====
  subgraph S["Single MCP Server"]
    direction TB
    WG["Webhook Ingest (Notion)"]
    CR["Context Registry"]
    
    subgraph ST["MCP Server Tools"]
      TLOG["conversation_log"]
      TEXT["extract"]
    end
    class WG,CR,TLOG,TEXT ownerJMCH

    subgraph AOBOX["Agent Orchestrator"]
      AO["AO Engine (LangGraph)"]
      subgraph AT["Agent Tools"]
        ACRQ["CR Query/Read"]
        ACRW["CR Write/Insert"]
        ANMCP["Notion MCP Tool"]
      end
    end
    class AO,ACRQ,ACRW,ANMCP ownerJB

    subgraph BO["Backoffice"]
      BO1["Registry Viewer"]
      BJOB["Background Jobs (Daily Digest)"]
      BO3["Agent Flow Monitor"]
    end
    class BO1,BO3 ownerHJW
  end

  C0 --> TLOG
  C0 --> TEXT
  TLOG --> AO
  TEXT --> AO
  AO --> ACRQ
  AO --> ACRW
  ACRQ --> CR
  ACRW --> CR
  AO --> ANMCP
  ANMCP --> T4
  T4 --> WG
  WG --> CR
  BO1 --- CR
  BO3 --- AO
  BJOB --> AO

  LLM["Llama Local Model"]
  class LLM neutral
  AO --- LLM
```

### 데이터 플로우

1. **Client Request**: AI 클라이언트가 MCP를 통해 대화 데이터 전송
2. **MCP Routing**: MCP Server가 요청을 적절한 도구 핸들러로 라우팅
3. **Agent Processing**: LangGraph orchestrator가 상태 노드를 통해 처리
4. **Context Storage**: 결과를 Context Registry에 저장
5. **Backoffice Access**: 웹 인터페이스를 통해 데이터 조회 및 관리

---

## Quick Start

```bash
# 1. 프로젝트 디렉토리로 이동
cd projects/ai-agent-orchestrator-team

# 2. 의존성 설치
uv sync

# 3. 환경 설정 (대화형)
uv run python scripts/setup_env.py

# 4. 데모 실행
uv run python start_demo.py

# 5. 브라우저에서 확인
# http://localhost:8003
```

✅ 5분이면 시작할 수 있습니다!

---

## 실행 방법

### 사전 준비

#### 1. uv 설치
```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 2. 의존성 설치 및 환경 설정
```bash
cd projects/ai-agent-orchestrator-team
uv sync

# 자동 환경 설정 (권장)
uv run python scripts/setup_env.py
```

`setup_env.py` 스크립트는 다음을 자동으로 설정합니다:
- `.env` 파일 생성
- LLM Provider 선택 및 설정
- Gmail OAuth 인증 (선택 사항)
- Notion/Slack 연동 설정 (선택 사항)

#### 3. 수동 설정 (선택 사항)

자동 설정을 건너뛰고 수동으로 설정하려면:

```bash
# env.example을 .env로 복사
cp env.example .env

# .env 파일을 편집하여 필요한 값 입력
```

**LLM Provider 옵션:**

- **LLaMA (via Ollama) (로컬, 무료, 권장)**: 
  - Ollama 설치 필요 (https://ollama.com/download)
  - `ollama pull llama3.2:3b` 명령으로 모델 다운로드
  - `start_demo.py` 실행 시 자동으로 Ollama 및 모델 확인
- **Upstage Solar (클라우드, 한국어 최적화)**: API 키 필요
- **OpenAI (클라우드, 범용)**: API 키 필요

**MCP 통합 (선택 사항):**

- **Gmail**: Google Cloud에서 OAuth 2.0 credentials 다운로드 필요
- **Notion**: Notion Integration Token 필요
- **Slack**: Slack Bot Token 필요

### 데모 실행

#### 방법 1: 통합 스크립트 (권장)
```bash
uv run python start_demo.py
```

#### 방법 2: 개별 컴포넌트 실행
```bash
# 터미널 1: Context Registry
uv run python context_registry/registry.py

# 터미널 2: Agent Orchestrator
uv run python agent_orchestrator/orchestrator.py

# 터미널 3: MCP Server
uv run python mcp_server/server.py

# 터미널 4: Backoffice UI
uv run python backoffice/app.py
```

### 서비스 URL

실행 후 다음 URL에서 각 서비스에 접근할 수 있습니다:

- **Backoffice UI**: http://localhost:8003
- **Agent Orchestrator**: http://localhost:8001
- **Context Registry**: http://localhost:8002
- **MCP Server**: http://localhost:8000/mcp (HTTP transport)

### AI 클라이언트 설정

Claude Desktop 또는 Cursor에서 MCP 서버를 사용하려면 설정 파일에 다음 내용을 추가하세요:

#### Claude Desktop
```json
{
  "mcpServers": {
    "ai-agent-orchestrator": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:8000/mcp"
      ]
    }
  }
}
```

**설정 파일 위치**:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

#### Cursor
```json
{
  "mcpServers": {
    "ai-agent-orchestrator": {
      "url": "http://localhost:8000/mcp",
      "transport": "http"
    }
  }
}
```

**설정 파일**: `.cursor/mcp.json` (워크스페이스 루트)

**주의사항**:
- MCP 서버는 HTTP transport (`http://localhost:8000/mcp`)로 실행됩니다
- `start_demo.py` 실행 시 자동으로 HTTP transport로 시작됩니다

**자세한 설정 방법은 `docs/CLIENT_SETUP_GUIDE.md`를 참조하세요.**

---

## 프로젝트 구조

```
projects/ai-agent-orchestrator-team/
├── agent_orchestrator/     # LangGraph StateGraph 로직 (🟡)
│   ├── orchestrator.py     # 메인 오케스트레이터
│   ├── llm_provider.py     # LLM 통합
│   ├── summarizer.py       # 요약 기능
│   ├── daily_briefing.py   # 일일 브리핑
│   └── model.py            # 데이터 모델
├── mcp_server/             # MCP 구현 (🟢)
│   ├── server.py           # MCP 서버
│   ├── gmail_mcp_client.py # Gmail 연동
│   ├── slack_mcp_client.py # Slack 연동
│   ├── notion_mcp_client.py# Notion 연동
│   ├── daily_briefing_collector.py  # 일일 브리핑 데이터 수집
│   ├── daily_briefing_runner.py     # 일일 브리핑 실행기
│   ├── briefing_analyzer.py         # 브리핑 분석
│   └── notion_formatter.py          # Notion 포맷터
├── context_registry/       # Context Registry (🟢)
│   └── registry.py         # 메인 레지스트리
├── backoffice/             # 웹 UI (🔵)
│   ├── app.py              # FastAPI 앱
│   ├── job_manager.py      # 작업 관리자
│   ├── job_executor.py     # 작업 실행기
│   └── templates/          # HTML 템플릿
├── client_configs/         # AI 클라이언트 설정 예시 (참고용)
│   ├── cursor.json         # Cursor 설정 예시
│   ├── claude_desktop.json # Claude Desktop 설정 예시
│   └── chatgpt_desktop.json# ChatGPT Desktop 설정 예시
├── scripts/                # 개발 및 설정 유틸리티
│   ├── setup_env.py        # 환경 설정 자동화 스크립트
│   ├── create_gmail_token.py # Gmail OAuth 토큰 생성
│   ├── dev.py              # 개발 명령어
│   └── kill_ports.py       # 포트 정리
├── docs/                   # 문서
│   ├── CLIENT_SETUP_GUIDE.md     # AI 클라이언트 설정 가이드
│   └── ENVIRONMENT_SETUP.md      # 환경 변수 설정 가이드
├── logs/                   # 애플리케이션 로그 (자동 생성)
├── pyproject.toml          # 프로젝트 설정
├── uv.lock                 # 의존성 잠금 파일
├── .env.example            # 환경 변수 템플릿
├── start_demo.py           # 데모 시작 스크립트
└── README.md               # 본 문서 (프로젝트 메인 가이드)
```

---

## 개발 가이드

### 개발 명령어

```bash
# 데모 시작 (권장)
uv run python start_demo.py

# 환경 설정
uv run python scripts/setup_env.py

# 포트 정리 (Windows)
python scripts/kill_ports.py

# 개별 컴포넌트 실행
uv run python mcp_server/server.py           # MCP Server
uv run python agent_orchestrator/orchestrator.py  # Agent Orchestrator
uv run python context_registry/registry.py        # Context Registry
uv run python backoffice/app.py                   # Backoffice UI
```

### 유용한 명령어

```bash
# 로그 확인 (Windows PowerShell)
Get-Content logs\backoffice_*.log -Tail 50 -Wait

# 프로세스 확인
netstat -ano | findstr :8003

# 데이터베이스 초기화 (주의!)
Remove-Item context_registry\context_registry.db
Remove-Item backoffice\jobs.db
```

### Git 워크플로우

1. **Feature 브랜치 생성**
   ```bash
   git checkout -b feature/member-name/feature-description
   ```

2. **변경사항 커밋**
   ```bash
   git add .
   git commit -m "feat: Add new feature"
   ```

3. **Pull Request 생성**
   - 코드 리뷰 요청
   - 최소 1명 이상 승인 필요

---

## 평가 기준 (Meta Llama Academy)

본 프로젝트는 다음 기준에 따라 평가됩니다:

- **Project Impact (20점)**: MCP를 활용한 실용적 솔루션
- **Innovation & Creativity (20점)**: LangGraph 기반 혁신적 워크플로우
- **Technical Implementation (25점)**: 시스템 완성도 및 안정성
- **Effective Use of AI (25점)**: LLaMA 모델의 효과적 활용
- **Presentation & Documentation (10점)**: 명확한 아키텍처 설명

---

## 참고 자료

### 공식 문서
- [MCP Specification](https://modelcontextprotocol.io/) - Model Context Protocol 공식 문서
- [LangGraph Documentation](https://python.langchain.com/docs/langgraph) - LangGraph 공식 문서
- [FastAPI](https://fastapi.tiangolo.com/) - 웹 프레임워크 문서
- [uv Documentation](https://docs.astral.sh/uv/) - Python 패키지 관리자

### AI & LLM
- [Meta Llama Academy](https://llamaacademy.kr/) - Workshop 정보
- [Ollama](https://ollama.com/) - 로컬 LLM 실행 플랫폼
- [Upstage AI](https://www.upstage.ai/) - Upstage Solar LLM 공식 사이트
- [OpenAI Platform](https://platform.openai.com/) - OpenAI API 문서

### MCP 통합
- [Gmail MCP Server](https://github.com/gongrzhe/server-gmail-autoauth-mcp) - Gmail 통합용 MCP 서버
- [Notion API](https://developers.notion.com/) - Notion API 문서
- [Google Cloud Console](https://console.cloud.google.com/) - Gmail OAuth 설정

### 프로젝트 문서
- `docs/CLIENT_SETUP_GUIDE.md` - Claude Desktop, Cursor 설정 가이드
- `docs/ENVIRONMENT_SETUP.md` - 환경 변수 상세 설정 가이드
- `.env.example` - 환경 변수 템플릿

---

## 라이선스

MIT License - 자세한 내용은 LICENSE 파일을 참조하세요.

---

**프로젝트**: Meta x Llama Academy 최종 프로젝트  
**팀명**: AI Agent Orchestrator Team  
**기간**: 2025년 9월 30일 ~ 10월 2일
