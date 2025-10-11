# AI Client 설정 가이드

AI Agent Orchestrator MCP 서버를 Claude Desktop 및 Cursor에서 사용하는 방법을 안내합니다.

---

## 사전 준비

### 1. AI Agent Orchestrator 실행

```bash
cd projects/ai-agent-orchestrator-team
uv run python start_demo.py
```

서버가 실행되면 다음 서비스가 시작됩니다:
- MCP Server: `stdio` (Claude Desktop, Cursor)
- Backoffice UI: `http://localhost:8003`

---

## Claude Desktop 설정

### 1. 설정 파일 위치

**Windows**:
```
%APPDATA%\Claude\claude_desktop_config.json
```

**macOS**:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux**:
```
~/.config/Claude/claude_desktop_config.json
```

### 2. 설정 추가

`claude_desktop_config.json` 파일을 열고 다음 내용을 추가합니다:

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

**주의사항**:
- MCP 서버가 HTTP transport로 실행되어야 합니다 (`http://localhost:8000/mcp`)
- `start_demo.py` 실행 시 MCP Server가 자동으로 HTTP transport로 시작됩니다
- `npx mcp-remote`는 자동으로 설치되므로 별도 설치 불필요

### 3. Claude Desktop 재시작

설정 파일을 저장한 후 Claude Desktop을 완전히 종료하고 다시 실행합니다.

### 4. 연결 확인

Claude Desktop에서 다음과 같이 테스트합니다:

```
"MCP 서버가 연결되었나요?"
```

정상 연결 시 다음 도구를 사용할 수 있습니다:
- **conversation_log**: 대화 저장
- **extract**: 과거 대화 검색

---

## Cursor 설정

### 1. 설정 파일 위치

Cursor 워크스페이스 루트에 `.cursorrules` 파일이 있는 경우, MCP 설정은 다음 위치에 있습니다:

**Cursor Settings**:
```
Settings > Features > Model Context Protocol
```

또는 프로젝트 루트에 `.cursor/mcp.json` 파일을 생성합니다.

### 2. 설정 추가

`.cursor/mcp.json` 파일을 생성하고 다음 내용을 추가합니다:

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

**주의사항**:
- MCP 서버가 HTTP transport로 실행되어야 합니다 (`http://localhost:8000/mcp`)
- `start_demo.py` 실행 시 MCP Server가 자동으로 HTTP transport로 시작됩니다
- Cursor는 `mcp-remote` 없이 직접 HTTP URL을 지정합니다

### 3. Cursor 재시작

설정 파일을 저장한 후 Cursor를 재시작합니다.

### 4. 연결 확인

Cursor에서 다음과 같이 테스트합니다:

```
"MCP 서버 상태를 확인해줘"
```

---

## MCP 도구 사용법

### conversation_log - 대화 저장

**용도**: 현재 대화를 Context Registry에 저장

**사용 예시**:
```
"지금까지 대화를 저장해줘"
"이 대화 내용을 기록해줘"
```

**파라미터**:
- `channel`: 세션 ID (자동 생성)
- `messages`: 전체 대화 내용 (JSON 문자열)
- `meta`: 메타데이터 (JSON 문자열)

---

### extract - 대화 검색

**용도**: 저장된 대화에서 정보 검색

**사용 예시**:
```
"Gmail 설정 관련 대화를 찾아줘"
"registry 관련 저장된 대화를 검색해줘"
```

**파라미터**:
- `query`: 검색 조건 (JSON 객체)
  - `text`: 검색 키워드
  - `limit`: 결과 개수 (기본값: 2)
- `channel`: 특정 세션 검색 (선택, 빈 문자열이면 전체 검색)

---

## 트러블슈팅

### Claude Desktop 연결 실패

1. **MCP 서버 실행 확인**
   ```bash
   # HTTP 서버 확인 (Windows PowerShell)
   curl http://localhost:8000/mcp
   ```

2. **로그 확인**
   ```bash
   # 로그 파일 확인
   Get-Content logs\mcp_server_*.log -Tail 50
   ```

3. **포트 확인**
   ```bash
   # 포트 8000이 사용 중인지 확인
   netstat -ano | findstr :8000
   ```

### Cursor 연결 실패

1. **MCP 서버 실행 확인**
   ```bash
   # HTTP 서버 확인
   curl http://localhost:8000/mcp
   ```

2. **설정 파일 확인**
   - `.cursor/mcp.json` 파일의 URL이 정확한지 확인
   - `"transport": "http"` 설정 확인

3. **서버 재시작**
   ```bash
   python scripts/kill_ports.py
   uv run python start_demo.py
   ```

---

## 설정 파일 예시

### Claude Desktop (Windows)

`%APPDATA%\Claude\claude_desktop_config.json`:

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

### Cursor (프로젝트 루트)

`.cursor/mcp.json`:

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

---

## 다음 단계

설정이 완료되면 다음 기능을 사용할 수 있습니다:

1. **대화 저장 및 검색**: conversation_log, extract 도구
2. **Backoffice UI**: `http://localhost:8003`
   - Dashboard: 시스템 상태
   - Registry: 저장된 대화 조회
   - Jobs: Daily Briefing 실행
3. **Daily Briefing**: Gmail, Slack, Notion 통합

자세한 내용은 `README.md`를 참조하세요.

