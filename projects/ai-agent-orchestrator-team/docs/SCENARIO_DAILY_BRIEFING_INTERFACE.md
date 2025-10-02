# 아침 브리핑 (Proactive) 인터페이스 정의서

## 📋 시나리오 개요

### 시나리오명
**개인 업무 데일리 브리핑 (Proactive Daily Work Briefing)**

### 목적
매일 아침 정해진 시간(07:00 KST)에 5개 외부 MCP 서버에서 업무 관련 데이터를 수집하여 AI가 통합 분석한 후, 우선순위별로 정리된 브리핑을 자동 생성하는 기능

### 핵심 요구사항
- 5개 MCP 서버 (Gmail, Slack, Notion, Google Drive, Google Calendar) 연동
- 매일 07:00 KST 자동 실행 (Proactive)
- LLaMA 모델을 활용한 우선순위 분석 및 요약
- Notion에 브리핑 페이지 자동 생성
- 전사적 업무 컨텍스트 통합 분석

---

## 🔄 전체 데이터 플로우

```mermaid
sequenceDiagram
    participant BO as Backoffice Scheduler
    participant AO as Agent Orchestrator
    participant CR as Context Registry
    participant EXT as External MCP Servers
    participant LLM as LLaMA Model
    participant Notion

    Note over BO: 1. 매일 07:00 KST 자동 트리거
    BO->>AO: daily_briefing 요청
    AO->>AO: plan (daily_briefing 작업 확인)

    Note over AO: 2. 외부 데이터 수집 단계
    AO->>EXT: external_action (Gmail - 긴급 이메일)
    EXT-->>AO: 우선순위 높은 이메일 목록
    AO->>EXT: external_action (Slack - 멘션/DM)
    EXT-->>AO: 읽지 않은 멘션 및 중요 메시지
    AO->>EXT: external_action (Calendar - 오늘 일정)
    EXT-->>AO: 오늘의 회의 및 이벤트 목록
    AO->>EXT: external_action (Drive - 최근 파일)
    EXT-->>AO: 어제부터 수정된 중요 문서
    AO->>EXT: external_action (Notion - 할 일)
    EXT-->>AO: 미완료 태스크 및 마감임박 항목

    Note over AO: 3. AI 통합 분석 단계
    AO->>AO: transform (데이터 전처리)
    AO->>LLM: 통합 데이터 분석 요청
    LLM-->>AO: 우선순위별 분석 결과
    AO->>AO: transform (브리핑 포맷팅)

    Note over AO: 4. 브리핑 생성 및 Notion 저장
    AO->>AO: 최종 브리핑 문서 생성 (Markdown 포맷)
    AO->>EXT: external_action (Notion 페이지 생성)
    Note over EXT, Notion: 브리핑 내용을 Notion 페이지로 생성
    EXT->>Notion: create-pages (브리핑 내용)
    Notion-->>EXT: 생성된 페이지 정보
    EXT-->>AO: 페이지 URL 및 생성 결과

    Note over AO: 5. 로그 저장 및 완료
    AO->>CR: cr_write (실행 로그 + Notion URL 저장)
    AO-->>BO: 브리핑 완료 응답 (Notion URL 포함)

    Note over Notion: 📊 최종 결과물
    Note over Notion: "📅 Daily Briefing - 2025-09-29"<br/>🔥 긴급 처리 항목 (3개)<br/>⭐ 중요 업무 (5개)<br/>📅 오늘 일정 요약<br/>📋 팀 관련 업데이트<br/>💡 추천 액션 아이템
```

### 상세 단계별 설명

1. **자동 트리거 (Proactive)**
   - Backoffice 스케줄러가 매일 07:00 KST에 daily_briefing 작업 실행
   - Agent Orchestrator로 작업 요청 전달

2. **외부 데이터 수집 (external_action)**
   - **Gmail**: 긴급 이메일, 읽지 않은 중요 메일 조회
   - **Slack**: 개인 멘션, DM, 중요 채널 메시지 수집
   - **Google Calendar**: 오늘의 회의 일정 및 이벤트 조회
   - **Google Drive**: 어제부터 수정된 중요 문서 목록
   - **Notion**: 미완료 태스크, 마감임박 항목 조회

3. **AI 통합 분석 (transform with LLaMA)**
   - 수집된 모든 데이터를 LLaMA 모델로 통합 분석
   - 우선순위 책정 (긴급도, 중요도, 의존성 고려)
   - 연관성 분석 (프로젝트별, 팀별 그룹핑)

4. **브리핑 생성 및 배포**
   - 분석 결과를 구조화된 브리핑 포맷으로 변환
   - Notion에 브리핑 페이지 자동 생성
   - Context Registry에 실행 로그 저장

---

## 🔧 요소기술별 인터페이스 정의

### 1. Backoffice Scheduler (담당: 황중원님)

#### 💡 **이 작업이 필요한 이유**
브리핑이 "Proactive(능동적)"이려면 사람이 매번 수동으로 실행하지 않고, 컴퓨터가 알아서 정해진 시간에 자동으로 실행되어야 합니다. 마치 스마트폰의 알람처럼 매일 아침 7시에 자동으로 "띵!" 하고 울리는 것처럼, 우리 시스템도 매일 아침 7시에 자동으로 브리핑을 만들어야 합니다.

#### 🔍 **구체적으로 해야 할 일**
1. **크론 스케줄러 설정**: 리눅스의 cron이나 Python의 APScheduler 같은 도구를 사용해서 "매일 07:00에 이 함수를 실행해라"라고 컴퓨터에게 명령을 내려놓는 것
2. **Agent Orchestrator 호출**: 시간이 되면 "아! 브리핑 만들 시간이야!"라고 하면서 실제 브리핑을 만드는 Agent Orchestrator에게 "일 시작해!"라고 신호를 보내는 것
3. **에러 처리**: 만약 브리핑 만들기가 실패하면 "다시 시도해볼게"라고 하면서 최대 3번까지 재시도하는 기능

#### 1.1 자동 트리거 기능

**목적**: 매일 정해진 시간에 브리핑 작업 자동 실행

**🤔 왜 이런 형태의 데이터가 필요한가요?**
스케줄러가 Agent Orchestrator에게 "브리핑 만들어줘!"라고 요청할 때, 단순히 "브리핑 만들어"라고만 하면 Agent Orchestrator는 "언제 것을? 뭘 포함해서?"라고 궁금해할 것입니다. 그래서 구체적인 정보를 함께 보내야 합니다.

**트리거 조건**
```python
{
    "schedule": "07:00 KST",
    "timezone": "Asia/Seoul",
    "enabled": True,
    "retry_on_failure": True,
    "max_retries": 3
}
```

**출력 (Backoffice → AO)**
```json
{
    "operation": "daily_briefing",
    "trigger_time": "2025-09-29T07:00:00+09:00",
    "source": "backoffice_scheduler",
    "config": {
        "target_date": "2025-09-29",
        "include_services": ["gmail", "slack", "notion", "calendar", "drive"],
        "priority_threshold": "medium"
    }
}
```

### 2. Agent Orchestrator (담당: 최현님)

#### 💡 **이 작업이 필요한 이유**
Agent Orchestrator는 우리 시스템의 "두뇌" 역할을 합니다. Backoffice에서 "브리핑 만들어줘!"라고 요청이 오면, "알겠어! 그럼 먼저 Gmail에서 이메일 가져오고, 그다음 Slack에서 메시지 가져오고, 그걸 다 분석해서 브리핑 만들어서 Notion에 저장할게!"라고 하면서 전체 과정을 단계별로 관리하는 역할입니다.

#### 🔍 **구체적으로 해야 할 일**
1. **StateGraph 설계**: LangGraph를 사용해서 브리핑 만드는 과정을 여러 단계로 나누어 설계 (plan → 데이터수집 → 분석 → 저장)
2. **MCP 서버 연동**: 5개 외부 서비스(Gmail, Slack 등)에서 데이터를 가져오는 기능
3. **LLaMA 모델 연동**: 가져온 데이터를 AI에게 분석시켜서 우선순위가 정리된 브리핑으로 만드는 기능
4. **에러 처리**: 중간에 뭔가 실패하면 "이 부분만 다시 해볼게" 또는 "일단 가능한 데이터로라도 브리핑 만들어볼게"라고 처리하는 기능

#### 🤖 **StateGraph가 뭔가요?**
StateGraph는 복잡한 작업을 여러 단계로 나누어서 순서대로 처리하는 방법입니다. 요리로 비유하면:
1. **plan**: "오늘 뭘 요리할지 계획 세우기"
2. **external_action**: "재료 사러 가기"
3. **transform**: "재료를 요리하기"
4. **cr_write**: "완성된 요리를 냉장고에 저장하기"

#### 2.1 Daily Briefing StateGraph 플로우

**범용 노드 활용 시나리오**
```python
# Daily Briefing 전용 플로우
daily_briefing_flow = {
    "plan": "daily_briefing 작업 타입 확인",
    "external_action": "5개 MCP 서버 데이터 수집",
    "transform": "LLaMA 기반 통합 분석 및 브리핑 생성",
    "external_action": "Notion 브리핑 페이지 생성",
    "cr_write": "실행 로그 Context Registry 저장"
}
```

**입력 (Backoffice → AO)**
```python
{
    "operation": "daily_briefing",
    "query": {
        "target_date": "2025-09-29",
        "services": ["gmail", "slack", "notion", "calendar", "drive"],
        "analysis_depth": "comprehensive"
    },
    "source": "backoffice_scheduler"
}
```

**출력 (AO → Backoffice)**
```python
{
    "success": True,
    "briefing_result": {
        "notion_page_url": "https://notion.so/workspace/daily-briefing-20250929",
        "summary": {
            "high_priority_items": 5,
            "meetings_today": 3,
            "urgent_emails": 2,
            "pending_tasks": 12
        },
        "execution_time": "127.5 seconds",
        "services_processed": ["gmail", "slack", "notion", "calendar", "drive"]
    },
    "timestamp": "2025-09-29T07:02:07+09:00"
}
```

#### 2.2 External Action 노드 상세

#### 🔍 **External Action이 뭐하는 건가요?**
External Action은 "외부에서 데이터 가져오기"를 담당합니다. 우리 시스템 밖에 있는 Gmail, Slack, Notion 등에서 정보를 가져와야 브리핑을 만들 수 있잖아요? 이때 각 서비스마다 "어떤 정보를 어떻게 가져올지" 구체적으로 정해야 합니다.

**🎯 각 서비스별로 왜 이런 데이터를 가져와야 할까요?**
- **Gmail**: 긴급한 이메일이나 중요한 이메일을 놓치면 큰일 나잖아요!
- **Slack**: 팀에서 나를 멘션했거나 직접 메시지를 보낸 건 확인해야죠
- **Notion**: 오늘까지 해야 할 일이나 마감 임박한 프로젝트를 알아야 해요
- **Calendar**: 오늘 회의가 몇 개나 있는지 미리 알아야 하루 계획을 세울 수 있어요
- **Drive**: 어제 누가 중요한 문서를 수정했는지 알면 놓친 업데이트를 파악할 수 있어요

**5개 MCP 서버별 데이터 수집**

**Gmail MCP 수집**
```python
{
    "action": "gmail_collect",
    "tools": ["search_emails", "read_email"],
    "query": {
        "search_terms": ["is:unread", "is:important", "has:attachment"],
        "time_range": "yesterday",
        "max_results": 20
    }
}
```

**Slack MCP 수집**
```python
{
    "action": "slack_collect",
    "tools": ["get_user_messages", "get_channel_history"],
    "query": {
        "message_types": ["mention", "direct_message"],
        "time_range": "yesterday",
        "channels": ["general", "dev-team", "project-alpha"]
    }
}
```

**Notion MCP 수집**
```python
{
    "action": "notion_collect",
    "tools": ["search", "fetch"],
    "query": {
        "database_types": ["tasks", "projects"],
        "filters": ["status != Done", "due_date <= today"],
        "sort": "priority desc"
    }
}
```

**Google Calendar MCP 수집**
```python
{
    "action": "calendar_collect",
    "tools": ["list_events", "get_free_busy"],
    "query": {
        "time_range": "today",
        "event_types": ["meeting", "deadline", "reminder"],
        "include_details": True
    }
}
```

**Google Drive MCP 수집**
```python
{
    "action": "drive_collect",
    "tools": ["gdrive_search", "gdrive_read_file"],
    "query": {
        "modified_since": "yesterday",
        "file_types": ["document", "spreadsheet", "presentation"],
        "shared_with_me": True
    }
}
```

#### 2.3 Transform 노드 (LLaMA 통합 분석)

#### 🤖 **Transform이 뭘 하는 건가요?**
5개 서비스에서 가져온 원본 데이터들(이메일, 메시지, 할일 등)을 그냥 나열만 하면 사람이 보기 어렵겠죠? 그래서 LLaMA AI에게 "이 데이터들을 보고 중요한 순서대로 정리해서 보기 좋은 브리핑으로 만들어줘"라고 요청하는 단계입니다.

#### 🎯 **왜 AI가 필요한가요?**
- **우선순위 판단**: n개의 이메일 중에서 정말 중요한 k개를 AI가 찾아줘요
- **연관성 파악**: "이 Slack 메시지와 이 Notion 태스크가 같은 프로젝트 얘기네!"라고 AI가 연결해줘요
- **요약**: 긴 이메일이나 문서 내용을 한 줄로 요약해줘요
- **구조화**: 뒤죽박죽인 정보들을 "긴급한 것", "중요한 것", "오늘 일정" 등으로 깔끔하게 분류해줘요

**LLaMA 분석 프롬프트 예시: 성능과 직결되는 부분으로 엔지니어링에 시간을 들여야 할 것 같습니다(e.g. Output Constraints, Priority Algorithms, etc.)
```
다음 5개 서비스에서 수집된 업무 데이터를 분석하여 오늘의 업무 브리핑을 생성해주세요:

[Gmail 데이터]: {gmail_data}
[Slack 메시지]: {slack_data}
[Notion 태스크]: {notion_data}
[Calendar 일정]: {calendar_data}
[Drive 문서]: {drive_data}

분석 기준:
1. 긴급도 (오늘 처리 필요, 마감 임박)
2. 중요도 (프로젝트 영향도, 의사결정 필요)
3. 연관성 (프로젝트별, 팀별 그룹핑)
4. 소요 시간 (예상 처리 시간)

출력 형식:
- 🔥 긴급 처리 항목 (Top 3)
- ⭐ 중요 업무 (Top 5)
- 📅 오늘 일정 요약
- 📋 팀 관련 업데이트
- 💡 추천 액션 아이템
```

### 3. External MCP Servers (담당: 이재범님, 이지민님)

#### 💡 **이 작업이 필요한 이유**
MCP(Model Context Protocol) 서버는 외부 서비스들과 우리 시스템을 연결해주는 "다리" 역할을 합니다. Gmail, Slack 등 각 서비스마다 다른 방식으로 데이터를 가져와야 하는데, MCP 서버가 이런 복잡한 과정을 표준화된 방식으로 처리해줍니다.

#### 🔍 **구체적으로 해야 할 일**
1. **5개 MCP 서버 설치 및 설정**: 각 서비스별로 미리 만들어진 MCP 서버를 설치하고 인증 정보 설정
2. **통합 데이터 수집 API 개발**: "Gmail에서 이메일 가져와줘", "Slack에서 메시지 가져와줘" 같은 요청을 처리하는 함수들 개발
3. **Notion 페이지 생성**: 완성된 브리핑을 Notion에 예쁘게 페이지로 만들어주는 기능
4. **에러 처리**: 특정 서비스가 응답하지 않을 때 "일단 다른 서비스 데이터로라도 브리핑 만들어보자" 처리

#### 🤔 **MCP가 뭔가요?**
MCP는 "AI 도구들이 외부 서비스와 쉽게 소통할 수 있게 해주는 표준 방법"입니다. 마치 USB가 모든 기기를 컴퓨터에 연결할 수 있게 해주는 것처럼, MCP는 모든 외부 서비스를 AI 시스템에 연결할 수 있게 해줍니다.

#### 3.1 MCP 서버 연동 설정

#### 🔐 **왜 이렇게 많은 인증 정보가 필요한가요?**
각 서비스(Gmail, Slack 등)는 보안을 위해 "너 누구야? 정말 이 데이터에 접근할 권한이 있어?"라고 확인합니다. 그래서 각 서비스마다 "열쇠"(인증 정보)가 필요해요. 이 열쇠들을 환경 변수로 안전하게 저장해두고 사용합니다.

**환경 변수 설정**
```json
{
    "GMAIL_CREDENTIALS": "/path/to/gmail-oauth.json",
    "SLACK_BOT_TOKEN": "xoxb-your-bot-token",
    "NOTION_API_KEY": "secret_notion_key",
    "GOOGLE_CALENDAR_CREDENTIALS": "/path/to/calendar-oauth.json",
    "GOOGLE_DRIVE_CREDENTIALS": "/path/to/drive-oauth.json"
}
```

**MCP 클라이언트 설정**
```json
{
    "mcpServers": {
        "gmail": {
            "command": "npx",
            "args": ["@gongrzhe/server-gmail-autoauth-mcp"]
        },
        "slack": {
            "command": "npx",
            "args": ["@modelcontextprotocol/server-slack"]
        },
        "notion": {
            "command": "npx",
            "args": ["@notionhq/notion-mcp-server"]
        },
        "google-calendar": {
            "command": "npx",
            "args": ["@cocal/google-calendar-mcp"]
        },
        "google-drive": {
            "command": "npx",
            "args": ["@isaacphi/mcp-gdrive"]
        }
    }
}
```

#### 개발 우선 순위

1. Notion(사실상 메인 기능이며, 공식 MCP 서버가 있어 배움에 유리할 듯), Slack(토큰만 있으면 쉬움), Gmail(기본 기능들만 연동)

2. Google Calendar & Google Drive(시간 허용 시)

#### 3.2 통합 데이터 수집 API

#### 🎯 **이 API가 하는 일**
Agent Orchestrator가 "Gmail에서 데이터 가져와줘"라고 요청하면, 이 API가 실제로 Gmail MCP 서버에 연결해서 데이터를 가져오고, 사용하기 좋은 형태로 정리해서 돌려주는 역할을 합니다. 마치 "심부름꾼"처럼 여러 곳에서 정보를 수집해서 한곳에 모아주는 거예요.

**함수 시그니처**
```python
async def collect_daily_briefing_data(
    target_date: str,
    services: List[str] = ["gmail", "slack", "notion", "calendar", "drive"]
) -> Dict[str, Any]:
    """
    5개 MCP 서버에서 브리핑용 데이터 수집

    Returns:
        서비스별 수집 데이터 및 메타정보
    """
```

**출력 데이터 구조**
```python
{
    "gmail": {
        "urgent_emails": [
            {
                "subject": "긴급: 프로젝트 승인 요청",
                "sender": "manager@company.com",
                "priority": "high",
                "received_time": "2025-09-28T18:30:00Z"
            }
        ],
        "count": 2
    },
    "slack": {
        "mentions": [
            {
                "channel": "#dev-team",
                "message": "@username 코드 리뷰 부탁드립니다",
                "sender": "developer1",
                "timestamp": "2025-09-28T17:45:00Z"
            }
        ],
        "count": 3
    },
    "notion": {
        "pending_tasks": [
            {
                "title": "API 문서 업데이트",
                "status": "In Progress",
                "due_date": "2025-09-29",
                "priority": "High"
            }
        ],
        "count": 12
    },
    "calendar": {
        "today_events": [
            {
                "title": "팀 스탠드업",
                "start_time": "2025-09-29T09:00:00+09:00",
                "duration": "30분",
                "attendees": 5
            }
        ],
        "count": 3
    },
    "drive": {
        "recent_documents": [
            {
                "title": "프로젝트 기획서 v2.0",
                "modified_time": "2025-09-28T16:20:00Z",
                "modified_by": "pm@company.com",
                "file_type": "document"
            }
        ],
        "count": 4
    }
}
```

### 4. Context Registry (담당: 이재범님, 이지민님)

#### 💡 **이 작업이 필요한 이유**
Context Registry는 우리 시스템의 "기록보관소" 역할을 합니다. 매일 브리핑을 만들 때마다 "언제 실행했는지", "어떤 데이터를 수집했는지", "결과가 어땠는지" 등을 모두 기록해둬야 해요. 나중에 "어? 어제 브리핑이 왜 이상하지?" 할 때 로그를 보고 문제를 찾을 수 있거든요.

#### 🔍 **구체적으로 해야 할 일**
1. **브리핑 로그 테이블 설계**: 매일 브리핑 실행 정보를 저장할 데이터베이스 테이블 만들기
2. **저장 API 개발**: Agent Orchestrator에서 "브리핑 완료했어! 이 정보 저장해줘"라고 요청할 때 데이터를 저장하는 함수
3. **조회 기능**: "지난주 브리핑들 어떻게 실행됐는지 보여줘" 같은 요청 처리
4. **통계 기능**: "이번 달 브리핑 성공률이 얼마야?" 같은 분석 정보 제공

#### 4.1 브리핑 실행 로그 스키마

#### 📝 **각 필드가 왜 필요한가요?**
- **execution_date**: "어느 날 브리핑인지" - 날짜별로 찾을 때 필요
- **start_time/end_time**: "언제 시작해서 언제 끝났는지" - 성능 분석용
- **status**: "성공했는지 실패했는지" - 문제 파악용
- **services_data**: "어떤 데이터를 수집했는지" - 나중에 재분석할 때 필요
- **notion_page_url**: "브리핑이 어디에 저장됐는지" - 사용자가 찾을 수 있게

**daily_briefing_log 테이블**
```sql
CREATE TABLE daily_briefing_log (
    id TEXT PRIMARY KEY,
    execution_date DATE NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    status TEXT NOT NULL, -- 'running', 'completed', 'failed'
    services_data JSON, -- 수집된 원본 데이터
    analysis_result JSON, -- LLaMA 분석 결과
    notion_page_url TEXT,
    error_message TEXT,
    execution_duration INTEGER, -- seconds
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_execution_date (execution_date),
    INDEX idx_status (status)
);
```

#### 4.2 저장 API

**함수 시그니처**
```python
async def store_daily_briefing_log(
    execution_date: str,
    services_data: Dict[str, Any],
    analysis_result: Dict[str, Any],
    notion_page_url: str = None,
    status: str = "completed"
) -> str:
    """
    데일리 브리핑 실행 로그 저장

    Returns:
        저장된 로그 ID
    """
```

---

## 📊 브리핑 출력 포맷

### Notion 페이지 템플릿

```markdown
# 📅 Daily Briefing - 2025년 9월 29일

## 🔥 긴급 처리 항목 (Top 3)
1. **[Gmail]** 프로젝트 승인 요청 - manager@company.com (18:30 수신)
2. **[Notion]** API 문서 업데이트 - 오늘 마감 (우선순위: High)
3. **[Slack]** 코드 리뷰 요청 - #dev-team (17:45 멘션)

## ⭐ 중요 업무 (Top 5)
1. **프로젝트 Alpha 킥오프 미팅** (10:00-11:00) - 참석자 8명
2. **클라이언트 제안서 검토** - Drive에서 어제 16:20 업데이트됨
3. **팀 1:1 미팅 준비** (14:00-15:00)
4. **데이터베이스 마이그레이션 계획** - Notion 태스크 (진행중)
5. **Q3 보고서 최종 검토** - 내일 마감

## 📅 오늘 일정 요약 (3개 이벤트)
- **09:00-09:30** 팀 스탠드업 (5명 참석)
- **10:00-11:00** 프로젝트 Alpha 킥오프 (8명 참석)
- **14:00-15:00** 팀 1:1 미팅 (2명 참석)

## 📋 팀 관련 업데이트
- **#dev-team**: 새로운 배포 스크립트 논의 진행중
- **#project-alpha**: 기획서 v2.0 업데이트 완료 (PM팀)
- **Drive 공유**: 어제 4개 문서 업데이트됨

## 💡 추천 액션 아이템
1. 긴급 이메일 2건 오전 중 처리 필요
2. 코드 리뷰 요청 우선 대응
3. 킥오프 미팅 전 자료 미리 검토
4. API 문서 업데이트 오늘 내 완료

---
🤖 Generated by AI Agent Orchestrator at 2025-09-29 07:02:07 KST
```

---

## 📦 메시지 포맷 규약

### 공통 필드 정의

| 필드명 | 타입 | 필수 | 설명 |
|--------|------|------|------|
| operation | string | ✅ | 작업 타입 ("daily_briefing") |
| execution_date | string | ✅ | 브리핑 대상 날짜 (YYYY-MM-DD) |
| trigger_source | string | ✅ | 트리거 소스 (backoffice_scheduler) |
| services | array | ✅ | 수집 대상 서비스 목록 |

### 브리핑 결과 구조

```typescript
interface DailyBriefingResult {
    success: boolean;
    execution_id: string;
    execution_time: number; // seconds
    briefing_data: {
        urgent_items: BriefingItem[];
        important_tasks: BriefingItem[];
        todays_schedule: CalendarEvent[];
        team_updates: TeamUpdate[];
        action_items: ActionItem[];
    };
    notion_page_url?: string;
    error?: ErrorInfo;
}

interface BriefingItem {
    title: string;
    source: 'gmail' | 'slack' | 'notion' | 'calendar' | 'drive';
    priority: 'urgent' | 'high' | 'medium' | 'low';
    due_time?: string;
    description: string;
    related_people?: string[];
}
```

### 에러 코드 정의

| 코드 | 설명 | HTTP 상태 |
|------|------|-----------|
| MCP_CONNECTION_ERROR | 외부 MCP 서버 연결 실패 | 503 |
| LLAMA_ANALYSIS_ERROR | LLaMA 모델 분석 실패 | 500 |
| NOTION_CREATE_ERROR | Notion 페이지 생성 실패 | 502 |
| DATA_COLLECTION_ERROR | 데이터 수집 부분 실패 | 206 |
| SCHEDULER_ERROR | 스케줄러 실행 오류 | 500 |

---

## ✅ 구현 체크리스트

### Backoffice Scheduler (황중원님)
- [ ] 07:00 KST 자동 트리거 구현
  - [ ] 크론 스케줄러 설정
  - [ ] 재시도 로직 (최대 3회)
  - [ ] 실행 상태 모니터링
- [ ] Agent Orchestrator 호출 API
- [ ] 실행 결과 로깅 UI

### Agent Orchestrator (최현님)
- [ ] Daily Briefing StateGraph 플로우
  - [ ] plan 노드 (daily_briefing 타입 처리)
  - [ ] external_action 노드 (5개 MCP 서버 연동)
  - [ ] transform 노드 (LLaMA 통합 분석)
  - [ ] cr_write 노드 (실행 로그 저장)
- [ ] LLaMA 모델 통합
  - [ ] 브리핑 분석 프롬프트 설계
  - [ ] 우선순위 책정 알고리즘
- [ ] 에러 핸들링 및 복구 로직

### External MCP Integration (이재범님, 이지민님)
- [ ] 5개 MCP 서버 연동
  - [ ] Gmail MCP 데이터 수집
  - [ ] Slack MCP 메시지 조회
  - [ ] Notion MCP 태스크 조회
  - [ ] Google Calendar 일정 조회
  - [ ] Google Drive 문서 조회
- [ ] 통합 데이터 수집 API
- [ ] Notion 브리핑 페이지 생성 기능
- [ ] Rate Limit 처리 및 최적화

### Context Registry (이재범님, 이지민님)
- [ ] daily_briefing_log 테이블 설계
- [ ] 브리핑 실행 로그 저장 API
- [ ] 통계 및 조회 기능
- [ ] 데이터 보관 정책 (30일)

---

## 🧪 테스트 시나리오

### 시나리오 1: 정상 브리핑 생성
1. 07:00 KST 자동 트리거 실행
2. 5개 MCP 서버에서 데이터 정상 수집
3. LLaMA 분석 및 우선순위 책정 완료
4. Notion 브리핑 페이지 생성 성공
5. 전체 실행 시간 < 3분

### 시나리오 2: 부분 실패 처리
1. Gmail, Slack 데이터 수집 성공
2. Calendar MCP 연결 실패 (timeout)
3. 수집 가능한 데이터로 브리핑 생성
4. 실패한 서비스 로그 기록
5. 재시도 메커니즘 동작 확인

### 시나리오 3: LLaMA 분석 오류
1. 모든 MCP 데이터 수집 성공
2. LLaMA 모델 분석 중 오류 발생
3. 기본 템플릿으로 브리핑 생성
4. 에러 상태로 로그 저장
5. 관리자 알림 발송

### 시나리오 4: 대용량 데이터 처리
1. 50+ 이메일, 100+ Slack 메시지 수집
2. 데이터 전처리 및 필터링
3. LLaMA 토큰 제한 내 분석 처리
4. 성능 측정 (메모리, CPU 사용량)

---

## 📅 예상 일정

| 단계 | 작업 내용 | 담당자 | 예상 시간 |
|------|----------|--------|-----------|
| 1 | MCP 서버 연동 설정 | 이재범 | 4시간 |
| 2 | Agent Orchestrator 플로우 | 최현 | 3시간 |
| 3 | Backoffice 스케줄러 | 황중원 | 2시간 |
| 4 | Context Registry 확장 | 이지민 | 2시간 |
| 5 | LLaMA 모델 통합 | 최현 | 3시간 |
| 6 | 통합 테스트 | 전체 | 2시간 |
| 7 | 버그 수정 및 최적화 | 전체 | 2시간 |

**총 예상 시간**: 18시간 (3일 분산)

---

## 📌 주의사항

1. **Rate Limit 관리**
   - Notion: 180 req/min 제한 준수
   - Gmail: API 할당량 모니터링
   - 각 서비스별 지연 시간 적용

2. **데이터 프라이버시**
   - 개인정보 포함 메시지 필터링
   - 민감한 업무 정보 마스킹 처리
   - 로그 데이터 암호화 저장

3. **시간대 처리**
   - 모든 시간 데이터 KST 기준 통일
   - Daylight Saving Time 고려

4. **성능 최적화**
   - 병렬 데이터 수집으로 실행 시간 단축
   - LLaMA 모델 응답 시간 모니터링
   - 메모리 사용량 최적화

5. **장애 복구**
   - 개별 MCP 서버 실패 시 나머지 서비스 계속 진행
   - 브리핑 생성 실패 시 다음날 재시도
   - 수동 브리핑 트리거 기능 제공

---

## 끄적임

: 워크샵 종료 이후에도 짬 내서 develop 한다는 가정 하에 도전해보면 좋을 것 같은 기능들을 끄적여봅니다.

1. 개발/운영 환경 설정

* Docker Container(RDB는 PSQL, MySQL 등으로 upgrade)으로 개발 환경 설정

* Cloud Computing 서비스 프리 티어 이용하여 배포 및 자동화

2. Fine-tuning

* 저희 sLLM에게 tool-calling을 직접 가르치는 것도 실습의 목적에서는 괜찮아보입니다. NeurIPS 2023 Oral 논문 [Toolformer](https://openreview.net/forum?id=Yacmpz84TH)에서는 Self-supervised Learning을 통해 LM에게 "Tool이 필요하다고 판단되는 부분에서 알아서 \<툴 호출\>이라는 토큰을 생성해서 출력 문장을 완성하세요"라는 컨셉으로 학습시켰더라구요. 논문에서 사용한 모델이 6.7B임을 감안했을 때 학습했을 때 성능은 어느 정도 보장될 것 같아요...!

* 소수의 Gold Label 데이터들 저희가 가내수공업한 뒤에 프론티어 급 LLM(GPT5, Gemini 2.5 Pro 등)에 Few-shot Prompting으로 데이터셋 대량으로 찍어내면 될 것 같아요. 데이터셋 구축은 상기 논문 3페이지 Figure만 보셔도 이해 되실 겁니다!

3. PO(Preference Optimization)

* 답변 품질에 대한 사용자의 피드백(ChatGPT 생성 답변에 '좋아요'를 누르는 기능)을 반영하는 겁니다. 전통 RL처럼 별도의 보상 모델이 필요한 경우도 있지만, DPO와 같이 피드백을 바로 LM에 학습시키는 방법도 있습니다. LGAI에서 개발하는 언어 모델 EXAONE의 4.0 버전에서는 GRPO라고 쉽게 생각하면 고객 세그먼트를 분류해서, 세그먼트 별 선호도를 종합적으로 분석하는 방법도 제시하더군요.

* 이게 들어간다면 피드백 관련 DB 설계, PO Approach 채택 및 개발, 피드백 학습 자동화(MLOps/LLMOps) 등 할 일이 기하급수적으로 많아지긴 할 거에요...