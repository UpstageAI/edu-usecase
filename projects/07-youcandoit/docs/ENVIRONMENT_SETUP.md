# 환경 설정 가이드

AI Agent Orchestrator 실행에 필요한 환경 변수 설정 방법을 안내합니다.

---

## Quick Start (권장)

### 자동 설정 스크립트 사용

```bash
cd projects/ai-agent-orchestrator-team
uv run python scripts/setup_env.py
```

대화형으로 다음 항목을 설정할 수 있습니다:
1. LLM Provider 선택 (LLaMA/Ollama, Upstage, OpenAI)
2. Gmail OAuth 설정
3. Notion API 키
4. Slack 토큰

---

## LLM Provider 설정

3가지 LLM Provider를 지원합니다:

### 옵션 1: LLaMA (via Ollama) - 로컬, 무료 (권장)

#### 1. Ollama 설치

**Windows**:
```
https://ollama.com/download/windows
```

**macOS**:
```bash
brew install ollama
```

**Linux**:
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

#### 2. 모델 다운로드

```bash
ollama pull llama3.2:3b
```

#### 3. .env 설정

```bash
LLM_PROVIDER=llama
OLLAMA_MODEL=llama3.2:3b
OLLAMA_BASE_URL=http://localhost:11434/v1
```

#### 4. 확인

```bash
# Ollama가 실행 중인지 확인
curl http://localhost:11434

# start_demo.py 실행 시 자동으로 체크됨
uv run python start_demo.py
```

---

### 옵션 2: Upstage Solar - 클라우드, 한국어 최적화

#### 1. API 키 발급

1. Upstage Console 접속: https://console.upstage.ai/
2. 로그인 또는 회원가입
3. API Keys 메뉴에서 새 키 생성

#### 2. .env 설정

```bash
LLM_PROVIDER=upstage
UPSTAGE_API_KEY=up-your-api-key-here
UPSTAGE_MODEL=solar-pro2
UPSTAGE_BASE_URL=https://api.upstage.ai/v1/solar
```

---

### 옵션 3: OpenAI - 클라우드, 범용

#### 1. API 키 발급

1. OpenAI Platform 접속: https://platform.openai.com/
2. API keys 메뉴에서 새 키 생성

#### 2. .env 설정

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4-turbo-preview
```

---

## Gmail MCP 설정 (Daily Briefing용)

### 1. Google Cloud Project 설정

#### 1-1. 프로젝트 생성/선택

1. Google Cloud Console 접속: https://console.cloud.google.com/
2. 프로젝트 선택 또는 새 프로젝트 생성

#### 1-2. Gmail API 활성화

1. API 라이브러리 접속: https://console.cloud.google.com/apis/library
2. "Gmail API" 검색 후 선택
3. "사용 설정" 클릭

#### 1-3. OAuth 동의 화면 설정

1. https://console.cloud.google.com/apis/credentials/consent 접속
2. 다음 정보 입력:
   - 앱 이름: 원하는 이름 (예: "My Daily Briefing")
   - 사용자 지원 이메일: 본인 이메일
   - 개발자 연락처: 본인 이메일

3. **범위(Scopes) 추가**:
   - "범위 추가 또는 삭제" 클릭
   - 다음 두 범위 추가:
     - `.../auth/gmail.modify`
     - `.../auth/gmail.settings.basic`

4. **테스트 사용자 추가** (중요!):
   - "테스트 사용자" 섹션에서 "+ ADD USERS" 클릭
   - Daily Briefing에 사용할 Gmail 주소 입력
   - 예: `your-email@gmail.com`

#### 1-4. OAuth 클라이언트 ID 생성

1. https://console.cloud.google.com/apis/credentials 접속
2. "+ 사용자 인증 정보 만들기" > "OAuth 클라이언트 ID"
3. 애플리케이션 유형: **데스크톱 앱**
4. 이름: 원하는 이름 (예: "Daily Briefing Desktop")
5. "만들기" 클릭
6. **JSON 파일 다운로드** (예: `client_secret_xxx.apps.googleusercontent.com.json`)

### 2. Gmail MCP 인증

#### 자동 방법 (권장)

```bash
cd projects/ai-agent-orchestrator-team
uv run python scripts/setup_env.py
```

1. "Gmail Credentials JSON 파일 경로"를 물어볼 때 다운로드한 JSON 파일 경로 입력
2. 자동으로 `~/.gmail-mcp/gcp-oauth.keys.json`으로 복사됨
3. 브라우저가 열리면 Google 로그인 및 권한 승인
4. 인증 완료

#### 수동 방법

```bash
# 1. 디렉토리 생성
mkdir ~/.gmail-mcp

# 2. 다운로드한 JSON 파일 복사
cp ~/Downloads/client_secret_xxx.json ~/.gmail-mcp/gcp-oauth.keys.json

# 3. OAuth 인증 실행
npx -y @gongrzhe/server-gmail-autoauth-mcp auth

# 4. 브라우저에서 Google 로그인 및 권한 승인
```

### 3. .env 설정

```bash
# Gmail MCP (선택 - 기본값은 ~/.gmail-mcp/credentials.json)
GMAIL_CREDENTIALS=~/.gmail-mcp/gcp-oauth.keys.json
GMAIL_TOKEN_PATH=~/.gmail-mcp/credentials.json
```

### 4. 확인

```bash
# 인증 파일 확인
ls ~/.gmail-mcp/
# gcp-oauth.keys.json
# credentials.json

# start_demo.py 실행 시 Gmail MCP가 정상 동작하는지 확인
uv run python start_demo.py
```

---

## Notion MCP 설정 (Daily Briefing용)

### 1. Notion Integration 생성

1. Notion Integrations 페이지 접속: https://www.notion.so/my-integrations
2. "+ New integration" 클릭
3. 정보 입력:
   - Name: 원하는 이름 (예: "Daily Briefing Bot")
   - Associated workspace: 사용할 워크스페이스 선택
4. "Submit" 클릭
5. **Internal Integration Token** 복사 (예: `secret_xxx`)

### 2. Notion 페이지 권한 설정

1. Notion에서 Daily Briefing 결과를 저장할 **부모 페이지** 열기
2. 페이지 우측 상단 "..." 메뉴 클릭
3. "Add connections" 선택
4. 생성한 Integration 선택 (예: "Daily Briefing Bot")

### 3. 부모 페이지 ID 확인

페이지 URL에서 ID를 복사합니다:
```
https://www.notion.so/My-Page-1234567890abcdef1234567890abcdef
                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                           이 부분이 페이지 ID입니다
```

### 4. .env 설정

```bash
# Notion MCP
NOTION_API_KEY=secret_your_notion_integration_token
NOTION_BRIEFING_PARENT_PAGE_ID=your-parent-page-id
```

---

## Slack MCP 설정 (Daily Briefing용, 선택사항)

### 1. Slack App 생성

1. Slack API 페이지 접속: https://api.slack.com/apps
2. "Create New App" 클릭
3. "From scratch" 선택
4. App 이름과 워크스페이스 선택

### 2. 권한 설정

1. "OAuth & Permissions" 메뉴로 이동
2. "Scopes" 섹션에서 다음 권한 추가:
   - `channels:history`
   - `channels:read`
   - `users:read`
   - `im:history`
   - `im:read`

### 3. 토큰 발급

1. "Install to Workspace" 버튼 클릭
2. 권한 승인
3. **User OAuth Token** 복사 (예: `xoxp-xxx`)

### 4. .env 설정

```bash
# Slack MCP
SLACK_MCP_XOXP_TOKEN=xoxp-your-slack-user-token
```

---

## 서버 설정 (기본값 사용 권장)

```bash
# Server Ports
AGENT_PORT=8001
CONTEXT_REGISTRY_PORT=8002
BACKOFFICE_PORT=8003
MCP_SERVER_TRANSPORT=stdio

# Database Paths
CONTEXT_REGISTRY_DB_PATH=context_registry/context_registry.db
BACKOFFICE_DB_PATH=backoffice/jobs.db

# Logging
LOG_LEVEL=INFO

# Daily Briefing Schedule
BRIEFING_CRON_SCHEDULE=0 7 * * *  # 매일 07:00 KST
```

---

## 전체 .env 예시

```bash
# =============================================================================
# LLM Provider Settings
# =============================================================================
LLM_PROVIDER=llama

# LLaMA (via Ollama)
OLLAMA_MODEL=llama3.2:3b
OLLAMA_BASE_URL=http://localhost:11434/v1

# Upstage Solar (또는)
# LLM_PROVIDER=upstage
# UPSTAGE_API_KEY=up-your-api-key
# UPSTAGE_MODEL=solar-pro2

# OpenAI (또는)
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-your-api-key
# OPENAI_MODEL=gpt-4-turbo-preview

# =============================================================================
# MCP Server Settings
# =============================================================================

# Gmail MCP
GMAIL_CREDENTIALS=~/.gmail-mcp/gcp-oauth.keys.json
GMAIL_TOKEN_PATH=~/.gmail-mcp/credentials.json

# Notion MCP
NOTION_API_KEY=secret_your_notion_integration_token
NOTION_BRIEFING_PARENT_PAGE_ID=your-parent-page-id

# Slack MCP (선택)
SLACK_MCP_XOXP_TOKEN=xoxp-your-slack-user-token

# =============================================================================
# Server Configuration
# =============================================================================
AGENT_PORT=8001
CONTEXT_REGISTRY_PORT=8002
BACKOFFICE_PORT=8003
MCP_SERVER_TRANSPORT=stdio

CONTEXT_REGISTRY_DB_PATH=context_registry/context_registry.db
BACKOFFICE_DB_PATH=backoffice/jobs.db

LOG_LEVEL=INFO

# Daily Briefing Schedule (cron format)
BRIEFING_CRON_SCHEDULE=0 7 * * *
```

---

## 트러블슈팅

### Ollama 관련

**문제**: `Ollama is not running`
```bash
# Ollama 실행 확인
curl http://localhost:11434

# Ollama 수동 시작 (백그라운드)
ollama serve
```

**문제**: `Model 'llama3.2:3b' is not available`
```bash
# 모델 다운로드
ollama pull llama3.2:3b

# 설치된 모델 확인
ollama list
```

### Gmail OAuth 관련

**문제**: `403 Access Denied`
- OAuth 동의 화면에서 **테스트 사용자**에 Gmail 주소 추가했는지 확인
- Gmail API가 활성화되어 있는지 확인

**문제**: `Invalid client`
- `client_secret.json` 파일이 올바른지 확인
- Google Cloud Project가 정확한지 확인

### Notion API 관련

**문제**: `401 Unauthorized`
- Integration Token이 올바른지 확인
- Notion 페이지에 Integration을 연결했는지 확인

---

## 다음 단계

환경 설정이 완료되면:

1. **서버 실행**:
   ```bash
   uv run python start_demo.py
   ```

2. **Backoffice UI 확인**:
   - http://localhost:8003

3. **Daily Briefing 테스트**:
   - Backoffice > Jobs 페이지에서 "ambient" Job 활성화
   - 또는 수동 실행:
     ```bash
     uv run python mcp_server/daily_briefing_runner.py
     ```

4. **AI Client 연결**:
   - `docs/CLIENT_SETUP_GUIDE.md` 참조

자세한 내용은 `README.md`를 참조하세요.

