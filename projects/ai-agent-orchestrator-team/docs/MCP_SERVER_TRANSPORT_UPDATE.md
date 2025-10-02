# MCP Server Transport 업데이트 및 Cursor 통합

**작성일**: 2025년 10월 1일  
**작성자**: 황중원  
**브랜치**: feature/hjw/ai-tool-interaction → main  
**커밋**: ff37add, 8e82b99

## 개요

MCP Server에 HTTP와 STDIO 듀얼 트랜스포트 지원을 추가하고, Windows 환경의 Cursor 에디터와의 통합을 개선했습니다. 이를 통해 다양한 AI 클라이언트 환경에서 유연하게 MCP 서버를 사용할 수 있게 되었습니다.

## 주요 변경사항

### 1. MCP Server 듀얼 트랜스포트 지원

#### 변경 파일
- `mcp_server/server.py`

#### 구현 내용
```python
# 명령줄 인자로 트랜스포트 모드 선택
parser.add_argument("--transport", choices=["stdio", "http"], default="http")
parser.add_argument("--port", type=int, default=8000)
parser.add_argument("--host", type=str, default="127.0.0.1")
```

**STDIO 모드** (표준 입출력)
- Claude Desktop, ChatGPT Desktop 등 네이티브 MCP 클라이언트용
- `uv run python mcp_server/server.py --transport stdio`
- 표준 입출력을 통한 통신으로 프로세스 간 직접 연결

**HTTP 모드** (Server-Sent Events)
- Cursor, 웹 기반 클라이언트용 (Windows 환경 권장)
- `uv run python mcp_server/server.py --transport http --port 8000`
- `/mcp` 엔드포인트를 통한 SSE (Server-Sent Events) 스트리밍
- FastMCP의 `streamable_http_app()` 활용

#### 기술적 상세
```python
if args.transport == "stdio":
    await mcp.run_stdio_async()
else:
    # FastMCP의 streamable HTTP app 생성
    app = mcp.streamable_http_app()
    
    # Uvicorn으로 서버 실행
    config = uvicorn.Config(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        access_log=True
    )
    server = uvicorn.Server(config)
    await server.serve()
```

### 2. Cursor 설정 업데이트

#### 변경 파일
- `client_configs/cursor.json`

#### 변경 내용
```json
{
  "mcpServers": {
    "ai-agent-orchestrator": {
      "command": "uv",
      "args": ["run", "python", "mcp_server/server.py", "--transport", "stdio"]
    }
  }
}
```

#### 설정 위치 (Windows)
- 글로벌: `%APPDATA%\Cursor\User\settings.json`
- 워크스페이스: `.vscode/settings.json` 또는 `.cursor/settings.json`

#### 적용 방법
1. Cursor 설정 파일에 위 내용 추가
2. Cursor 재시작
3. MCP 서버가 자동으로 시작되며 대화 시 자동 연동

### 3. 문서화

#### 새로운 문서
- `MCP_SERVER_SETUP.md`: MCP 서버 설정 및 사용 가이드

#### 주요 내용
- **서버 실행 방법**: HTTP/STDIO 모드별 실행 명령어
- **Cursor 설정**: Windows 환경에서의 설정 방법
- **사용 가능한 툴**: conversation_log, extract 사용 예시
- **동작 확인**: 연결 테스트 및 검증 방법
- **문제 해결**: 일반적인 오류 상황 대응 가이드

#### 업데이트된 문서
- `CLAUDE.md`: 최신 프로젝트 정보 및 아키텍처 반영

### 4. 추가 개선사항

#### Agent Orchestrator
- `agent_orchestrator/orchestrator.py`: 로깅 개선 및 에러 처리 강화

#### Context Registry
- `context_registry/registry.py`: 쿼리 성능 최적화 및 트랜잭션 관리 개선

#### Backoffice
- `backoffice/app.py`: 통계 대시보드 기능 향상

## 사용 시나리오

### 시나리오 1: Cursor에서 대화 저장 (Windows)

1. **MCP 서버 자동 시작**
   ```bash
   # Cursor가 자동으로 실행 (설정 파일 기반)
   uv run python mcp_server/server.py --transport stdio
   ```

2. **대화 중 저장**
   ```
   사용자: "이 대화를 저장해줘"
   AI: [conversation_log 툴 자동 호출]
   ```

3. **Context Registry에 저장**
   - Channel: `cursor_session_20251001_1400`
   - Messages: 대화 전체 내용 (role, text, timestamp)
   - Metadata: source="cursor"

### 시나리오 2: Claude Desktop에서 조회 (macOS/Linux)

1. **MCP 서버 연결**
   ```json
   // claude_desktop.json
   {
     "mcpServers": {
       "ai-agent-orchestrator": {
         "command": "uv",
         "args": ["run", "python", "mcp_server/server.py", "--transport", "stdio"]
       }
     }
   }
   ```

2. **저장된 대화 검색**
   ```
   사용자: "Cursor에서 피보나치 최적화 논의한 내용 찾아줘"
   AI: [extract 툴 호출]
   ```

3. **결과 반환**
   - Agent Orchestrator가 Context Registry 조회
   - 관련 대화 내용 요약하여 반환

### 시나리오 3: HTTP 모드로 개발 테스트

1. **서버 시작**
   ```bash
   uv run python mcp_server/server.py --transport http --port 8000
   ```

2. **엔드포인트 확인**
   - MCP 엔드포인트: `http://localhost:8000/mcp`
   - SSE 스트리밍으로 실시간 응답

3. **API 테스트**
   ```bash
   # 포트 확인
   netstat -ano | findstr :8000
   ```

## 아키텍처 영향

### 데이터 흐름 (업데이트)

```
[Cursor/Claude] → MCP Client Config
                     ↓
                  [MCP Server]
                (HTTP or STDIO)
                     ↓
              [Agent Orchestrator]
               (LangGraph StateGraph)
                     ↓
              [Context Registry]
                  (SQLite)
```

### 트랜스포트 비교

| 항목 | STDIO | HTTP |
|------|-------|------|
| **용도** | 네이티브 클라이언트 | 웹/원격 클라이언트 |
| **연결 방식** | 프로세스 파이프 | HTTP/SSE |
| **지연시간** | 매우 낮음 | 낮음 |
| **디버깅** | 어려움 | 쉬움 (로그 확인 가능) |
| **방화벽** | 영향 없음 | 포트 오픈 필요 |
| **권장 환경** | Claude Desktop, ChatGPT Desktop | Cursor (Windows), 커스텀 클라이언트 |

## 호환성 확인

### 재범님 작업과의 충돌 검사

**재범님 브랜치**: `feature/jaebeom/notion-report`

**변경 파일 비교**:
- 재범님: `mcp_server/notion_formatter.py`, `notion_mcp_client.py` 등 (신규 파일)
- 중원님: `mcp_server/server.py` (기존 파일 수정)

**머지 결과**: ✅ **충돌 없음**
```bash
git merge feature/hjw/ai-tool-interaction --no-commit --no-ff
# → Automatic merge went well; stopped before committing as requested
```

**이유**:
- 재범님은 Notion 통합 관련 **새로운 파일** 추가
- 중원님은 MCP Server 기존 파일의 **트랜스포트 로직** 수정
- 수정 영역이 독립적이며 상호 보완적

### 통합 테스트 권장사항

1. **전체 시스템 시작**
   ```bash
   uv run python start_demo.py
   ```

2. **MCP 서버 연결 확인**
   - Cursor: STDIO 모드
   - Claude Desktop: STDIO 모드
   - HTTP 테스트: `http://localhost:8000/mcp`

3. **Notion 통합 테스트**
   - Daily Briefing 작업 실행
   - Notion 페이지 생성 확인
   - MCP 툴 연동 검증

## 참고 자료

### 관련 문서
- [MCP Protocol Specification](https://modelcontextprotocol.io/docs)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Agent Orchestrator Integration Guide](./AO_INTEGRATION_GUIDE.md)
- [Data Schema Specification](./DATA_SCHEMA_SPECIFICATION.md)

### 코드 참조
- MCP Server: `mcp_server/server.py` (lines 229-276)
- Cursor Config: `client_configs/cursor.json`
- Setup Guide: `MCP_SERVER_SETUP.md`

### 외부 링크
- [Cursor MCP Documentation](https://cursor.sh/docs/mcp)
- [Server-Sent Events (SSE) Spec](https://html.spec.whatwg.org/multipage/server-sent-events.html)

## 변경 이력

| 날짜 | 버전 | 변경 내용 | 작성자 |
|------|------|-----------|--------|
| 2025-10-01 | 1.0.0 | 초기 작성 - MCP Server 듀얼 트랜스포트 구현 | 황중원 |

## 문의사항

- **기술 문의**: 황중원 (GitHub: @HwangJohn)
- **이슈 등록**: https://github.com/HwangJohn/ai-prompt-history-llama/issues
- **PR 리뷰**: Team AI Agent Orchestrator

---

**Meta Llama Academy Workshop 2025**  
AI Agent Orchestrator Team

