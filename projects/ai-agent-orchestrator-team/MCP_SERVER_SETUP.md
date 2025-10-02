# MCP 서버 설정 가이드

## 서버 실행

### HTTP 모드 (권장 - Windows Cursor)
```bash
uv run python -m mcp_server.server --transport http --port 8000
```

서버는 `http://localhost:8000/mcp` 엔드포인트를 제공합니다.

### STDIO 모드
```bash
uv run python -m mcp_server.server --transport stdio
```

## Cursor 설정

Cursor의 설정 파일에 다음 내용을 추가합니다:

### Windows 경로
설정 파일 위치: `%APPDATA%\Cursor\User\settings.json` 또는 Cursor Settings UI

```json
{
  "mcpServers": {
    "ai-agent-orchestrator": {
      "url": "http://localhost:8000/mcp/v1",
      "transport": "http"
    }
  }
}
```

## 사용 가능한 툴

### 1. conversation_log
대화를 Context Registry에 저장합니다.

**예시:**
```
이 대화를 저장해줘
```

Cursor AI가 자동으로 `conversation_log` 툴을 호출하여 현재 대화를 저장합니다.

### 2. extract  
저장된 대화를 검색하고 조회합니다.

**예시:**
```
피보나치 최적화 관련 대화를 찾아줘
```

## 동작 확인

1. MCP 서버가 실행 중인지 확인:
   ```bash
   netstat -ano | findstr :8000
   ```

2. Cursor를 재시작하여 MCP 서버 연결

3. Cursor에서 대화 후 "이 대화를 저장해줘"라고 요청

4. 다른 세션에서 "저장된 대화를 찾아줘"라고 요청하여 조회

## 문제 해결

### 서버가 시작되지 않음
- 8000번 포트가 이미 사용 중인지 확인
- Python 프로세스 종료: `taskkill /F /IM python.exe`

### Cursor가 MCP 서버에 연결되지 않음
- Cursor를 재시작
- 설정 파일 경로가 올바른지 확인
- 서버 로그 확인

## Agent Orchestrator 연동

MCP 서버는 내부적으로 Agent Orchestrator를 호출합니다:
- `conversation_log` → Agent Orchestrator → Context Registry 저장
- `extract` → Agent Orchestrator → Context Registry 조회

모든 대화 데이터는 LangGraph StateGraph를 통해 처리됩니다.

