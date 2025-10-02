# MCP Server 설치 및 설정 가이드

**목적:** 3개 외부 MCP 서버 (Gmail, Slack, Notion)의 설치 및 인증 방법 안내

---

## 개요

이 프로젝트는 다음 3개의 외부 MCP 서버를 사용합니다:

1. **Gmail MCP** - `@gongrzhe/server-gmail-autoauth-mcp`
2. **Slack MCP** - `slack-mcp-server` (by korotovsky)
3. **Notion MCP** - `@notionhq/notion-mcp-server`

각 MCP 서버는 `npx`를 통해 자동으로 다운로드되지만, **사전에 인증(OAuth/API Key)이 필요**합니다.

---

## 1. Gmail MCP Server 설정

### 1.1 credentials.json 받기

**담당자(이재범)에게 `credentials.json` 파일을 받으세요.**

> **Note:** `credentials.json`은 이미 생성된 OAuth 클라이언트 ID입니다.
> Google Cloud Console 설정은 **불필요**합니다.

### 1.2 저장 및 OAuth 인증 (최초 1회)

```bash
# 디렉토리 생성
mkdir -p ~/.gmail-mcp

# 받은 credentials.json 파일 저장
cp credentials.json ~/.gmail-mcp/

# OAuth 인증 실행 (본인 Google 계정으로 인증)
npx -y @gongrzhe/server-gmail-autoauth-mcp auth

# 브라우저가 열리면:
# 1. Google 계정 로그인
# 2. Gmail API 권한 승인
# 3. 인증 완료 후 token.json 자동 생성됨
# 권한 오류 발생할 가능성이 상당히 높습니다
# 그 때는 담당자(이재범)에게 구글 계정 이메일 주소와 함께 권한 부여 요청해주세요
```

**생성된 파일 확인:**
```bash
ls -la ~/.gmail-mcp/
# credentials.json  - OAuth 클라이언트 ID (공유받은 파일)
# token.json        - 액세스 토큰 (본인 계정, 자동 갱신됨)
```

### 1.3 환경 변수 설정

```bash
# .env 파일에 추가(Windows 기준)
GMAIL_CREDENTIALS=C:/Users/your-username/.gmail-mcp/credentials.json
GMAIL_TOKEN_PATH=C:/Users/your-username/.gmail-mcp/token.json
```

---

## 2. Slack MCP Server 설정

### 2.1 Slack App 생성

1. **Slack API 페이지 접속**
   - https://api.slack.com/apps

2. **Create New App 클릭**
   - "From scratch" 선택
   - App Name: "Daily Briefing Bot" 등
   - Workspace 선택(태그, dm을 보는 만큼 여러 명이 활발히 사용하는 워크스페이스면 좋습니다)

3. **OAuth & Permissions 설정**
   - 좌측 메뉴: "OAuth & Permissions"
   - **User Token Scopes** 섹션에 다음 권한 추가:
     ```
     channels:history
     channels:read
     groups:history
     groups:read
     im:history
     im:read
     mpim:history
     mpim:read
     search:read
     users:read
     chat:write
     ```

4. **Install App to Workspace**
   - "Install to Workspace" 버튼 클릭
   - 권한 승인
   - **User OAuth Token** 복사 (xoxp-로 시작)

### 2.2 환경 변수 설정

```bash
# .env 파일에 추가
SLACK_MCP_XOXP_TOKEN=xoxp-your-slack-user-token-here
```

**⚠️ 주의사항:**
- **User Token** (`xoxp-`)을 사용해야 합니다 (Bot Token `xoxb-` 아님)
- User Token은 검색 기능을 위해 필요합니다

---

## 3. Notion MCP Server 설정

### 3.1 Notion Integration 생성

1. **Notion Integrations 페이지 접속**
   - https://www.notion.so/my-integrations

2. **New integration 클릭**
   - Name: "Daily Briefing Integration" 등
   - Associated workspace 선택
   - Capabilities:
     - ✅ Read content
     - ✅ Update content
     - ✅ Insert content
   - "Public" 말고 "Internal"로 만들어주세요
   - "Submit" 클릭

3. **Internal Integration Token 복사**

### 3.2 Notion 페이지/데이터베이스 공유

Integration이 접근할 페이지를 공유해야 합니다:

1. **Task Database 공유 (태스크 조회용)**
   - Notion에서 Task 관리 데이터베이스 열기
   - 우측 상단 `•••` 메뉴 > "Connections" > Integration 선택
   - "Confirm" 클릭

2. **Briefing Parent Page 공유 (Briefing 페이지 생성용)**
   - Daily Briefing을 생성할 부모 페이지 열기
   - 우측 상단 `•••` 메뉴 > "Connections" > Integration 선택
   - "Confirm" 클릭
   - 브리핑 페이지가 생성되지 않아서 이 부분은 나중에 해주세요!

3. **페이지 ID 확인**
   - 페이지 URL에서 ID 추출:
     ```
     https://www.notion.so/My-Tasks-abc123def456?pvs=4
                                  ^^^^^^^^^^^^
                                  이 부분이 ID
     My-Tasks-ab...456
     ```

### 3.3 환경 변수 설정

```bash
# .env 파일에 추가
NOTION_API_KEY=secret_your_notion_integration_token

# Task 관리 데이터베이스 ID (선택)
NOTION_DATABASE_ID=My-Tasks-ab...456

# Daily Briefing 페이지 생성할 부모 페이지 ID
NOTION_BRIEFING_PARENT_PAGE_ID=xyz789abc123...
```

---

## 4. 통합 테스트

모든 MCP 서버 설정이 완료되면 통합 테스트를 실행합니다:

```bash
# Daily Briefing Collector 테스트 (3개 MCP 병렬 호출)
uv run python mcp_server/daily_briefing_collector.py
```

**예상 출력:**
```
================================================================================
COLLECTION SUMMARY
================================================================================
Timestamp: 2025-10-01T02:07:10.654418
Period: 24 hours
Successful sources: 3/3
Failed sources: 0

--------------------------------------------------------------------------------
GMAIL
--------------------------------------------------------------------------------
✅ Status: success
📧 Emails collected: 14

--------------------------------------------------------------------------------
SLACK
--------------------------------------------------------------------------------
✅ Status: success
💬 Mentions: 0
📩 DMs: 0

--------------------------------------------------------------------------------
NOTION
--------------------------------------------------------------------------------
✅ Status: success
✓ Tasks collected: 2

================================================================================
Collection complete!
================================================================================
```

---

## 5. 환경 변수 전체 요약

`.env` 파일에 다음 변수들을 모두 설정하세요:

```bash
# ========================================
# Gmail MCP
# ========================================
GMAIL_CREDENTIALS=/Users/your-username/.gmail-mcp/credentials.json
GMAIL_TOKEN_PATH=/Users/your-username/.gmail-mcp/token.json

# ========================================
# Slack MCP
# ========================================
SLACK_MCP_XOXP_TOKEN=xoxp-your-slack-user-token

# ========================================
# Notion MCP
# ========================================
NOTION_API_KEY=secret_your_notion_integration_token
NOTION_DATABASE_ID=abc123def456...  # Task 데이터베이스 ID (선택)
NOTION_BRIEFING_PARENT_PAGE_ID=xyz789abc123...  # Briefing 부모 페이지 ID

# ========================================
# Other Services (필요시)
# ========================================
# Context Registry
CONTEXT_REGISTRY_URL=http://localhost:8002

# Agent Orchestrator
AGENT_ORCHESTRATOR_URL=http://localhost:8001
```

---

## 6. 트러블슈팅

### Gmail: "API has not been used in project"

**문제:**
```
Gmail API has not been used in project 732441520639 before or it is disabled
```

**해결:**
1. Google Cloud Console에서 Gmail API 활성화 확인
2. 5-10분 대기 후 재시도
3. 재인증 실행:
   ```bash
   npx -y @gongrzhe/server-gmail-autoauth-mcp auth
   ```

### Slack: "invalid_auth" 에러

**문제:**
```
{"ok": false, "error": "invalid_auth"}
```

**해결:**
1. User Token (`xoxp-`)인지 확인 (Bot Token `xoxb-` 아님)
2. Token이 올바르게 복사되었는지 확인 (공백 없음)
3. Workspace에 App이 설치되어 있는지 확인

### Notion: "Could not find database"

**문제:**
```
{"object": "error", "status": 404, "code": "object_not_found"}
```

**해결:**
1. Database/Page가 Integration과 공유되었는지 확인
   - 페이지 우측 상단 `•••` > "Connections" 확인
2. Database ID가 올바른지 확인
3. Integration에 "Read content" 권한이 있는지 확인

### npx 패키지 캐시 문제

**문제:**
MCP 서버가 최신 버전으로 업데이트되지 않음

**해결:**
```bash
# npx 캐시 삭제
npx clear-npx-cache

# 특정 패키지 재설치
npx -y @gongrzhe/server-gmail-autoauth-mcp --version
npx -y slack-mcp-server --version
npx -y @notionhq/notion-mcp-server --version
```

### Node.js 버전 문제

**요구사항:**
- Node.js 18 이상 필요

**확인:**
```bash
node --version
# v18.0.0 이상이어야 함
```

**설치 (Windows):**
- https://nodejs.org/ 에서 LTS 버전 다운로드

---

## 7. 보안 권장사항

### 인증 정보 관리

1. **운영 환경에서는 Secret Manager 사용**
   - AWS Secrets Manager
   - Google Secret Manager
   - Azure Key Vault

2. **Token 갱신 주기 확인**
   - Gmail: OAuth token 자동 갱신 (refresh token)
   - Slack: User token 만료 없음 (재발급 시 수동 교체)
   - Notion: Integration token 만료 없음

### 권한 최소화

각 MCP 서버에 필요한 최소 권한만 부여하세요:

- **Gmail**: 읽기 전용 (gmail.readonly)
- **Slack**: 읽기 + 메시지 전송 (search:read, chat:write)
- **Notion**: 특정 페이지/DB만 공유

---

## 문의

- 궁금하신 점은 담당자(이재범)에게 편하게 질문해주세요!