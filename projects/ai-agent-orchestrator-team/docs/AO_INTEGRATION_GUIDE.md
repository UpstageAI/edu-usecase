# Agent Orchestrator 통합 가이드

**대상:** Agent Orchestrator (AO) 담당자
**목적:** Daily Briefing 시나리오를 위한 MCP Client 및 Data Collector 사용 방법 안내

---

## 개요

Daily Briefing 시나리오는 다음과 같은 흐름으로 동작합니다. 아래 다이어그램 참고하시어, Backoffice에서 요청을 받아서 모든 비즈니스 로직 실행 후 레지스트리에 로그 저장 요청을 쏴주는 것까지 구현해주시면 됩니다:

```
Backoffice (Cron @07:00 KST)
    ↓
Agent Orchestrator (LangGraph StateGraph)
    ↓
Daily Briefing Collector (병렬 데이터 수집)
    ↓ ↓ ↓
Gmail MCP  Slack MCP  Notion MCP
    ↓
LLaMA (요약 및 우선순위 할당)
    ↓
Notion MCP (Briefing 페이지 생성)
    ↓
Context Registry (실행 로그 저장)
```

---

## 1. 데이터 수집 레이어 사용법

### 통합 API: `collect_daily_briefing_data()`

: 구현된 MCP 클라이언트들에게서 데이터를 일괄적으로 수집합니다.

**위치:** `mcp_server/daily_briefing_collector.py`

**사용 예시:**
```python
from mcp_server.daily_briefing_collector import collect_daily_briefing_data
import os

# LangGraph 노드 함수에서 호출
async def collect_data_node(state: BriefingState) -> BriefingState:
    """외부 MCP 서버에서 데이터 수집"""

    # 통합 데이터 수집 (병렬 처리)
    briefing_data = await collect_daily_briefing_data(
        hours=24,  # 최근 24시간 데이터
        notion_database_id=os.environ.get("NOTION_DATABASE_ID")
    )

    # State에 저장
    state["raw_data"] = briefing_data
    state["collection_timestamp"] = briefing_data["timestamp"]

    return state
```

### 반환 데이터 구조

```python
{
    "timestamp": "2025-10-01T02:07:10.654418",
    "period_hours": 24,
    "data": {
        "gmail": {
            "status": "success",  # "success" | "error" | "skipped"
            "count": 14,
            "emails": [
                {
                    "id": "19998423...",
                    "threadId": "19998423...",
                    "subject": "보안 알림",
                    "from": "Google <no-reply@accounts.google.com>",
                    "date": "Tue, 30 Sep 2025 16:23:34 GMT",
                    "body": "일부 Google 계정 데이터에 대한...",  # HTML 정제 완료
                    "snippet": ""
                }
            ],
            "error": null
        },
        "slack": {
            "status": "success",
            "count": 5,
            "mentions": [
                {
                    "ts": "1727654321.123456",
                    "user": "U01234567",
                    "text": "@you 리뷰 부탁드립니다",
                    "channel": "C01234567",
                    "channel_name": "dev-team",
                    "permalink": "https://...",
                    "timestamp": "1727654321.123456"
                }
            ],
            "dms": [],  # 현재는 빈 배열 (확장 가능)
            "error": null
        },
        "notion": {
            "status": "success",
            "count": 2,
            "tasks": [
                {
                    "id": "abc123...",
                    "title": "API 성능 개선",
                    "status": "In Progress",
                    "priority": "High",
                    "due_date": "2025-10-05",
                    "assignee": "jaebeom@example.com",
                    "url": "https://notion.so/..."
                }
            ],
            "error": null
        }
    },
    "summary": {
        "total_sources": 3,
        "successful_sources": 3,
        "failed_sources": 0
    }
}
```

### 에러 처리

**부분 실패 허용:**
- Gmail 실패해도 Slack/Notion은 계속 수집됨
- 각 소스의 `status` 필드로 성공/실패 확인

```python
async def collect_data_node(state: BriefingState) -> BriefingState:
    briefing_data = await collect_daily_briefing_data(hours=24)

    # 실패한 소스 확인
    failed_sources = []
    for source_name, source_data in briefing_data["data"].items():
        if source_data["status"] == "error":
            failed_sources.append({
                "source": source_name,
                "error": source_data["error"]
            })

    state["raw_data"] = briefing_data
    state["failed_sources"] = failed_sources

    # 모든 소스 실패 시 에러 처리
    if briefing_data["summary"]["successful_sources"] == 0:
        state["error"] = "All data sources failed"

    return state
```

---

## 2. LangGraph StateGraph 구조 제안

**AI가 뱉은 코드일 뿐입니다. 꼭 이대로 안 쓰셔도 돼요. 제 생각에는 설계는 직접 해보시고 그걸 토대로 개발해달라고 커서한테 프롬프트 쏴주는 게 가장 좋을 것 같습니다!**

### State 정의

```python
from typing import TypedDict, List, Dict, Any, Optional

class BriefingState(TypedDict):
    """Daily Briefing 워크플로우 상태"""

    # 입력
    trigger_time: str           # Backoffice에서 전달된 트리거 시간
    hours: int                  # 조회 기간 (기본 24시간)

    # 데이터 수집
    raw_data: Dict[str, Any]    # collect_daily_briefing_data() 반환값
    collection_timestamp: str
    failed_sources: List[str]

    # 데이터 가공
    filtered_data: Dict[str, Any]  # 필터링된 데이터
    prioritized_items: List[Dict]  # 우선순위 할당된 항목들

    # LLaMA 요약
    summary: str                # 생성된 요약문
    action_items: List[str]     # 추출된 액션 아이템

    # Notion 페이지 생성
    notion_page_id: str         # 생성된 Notion 페이지 ID
    notion_page_url: str        # 생성된 Notion 페이지 URL

    # 로그 저장
    log_id: str                 # Context Registry에 저장된 로그 ID

    # 에러
    error: Optional[str]
```

### 노드 구성 예시

```python
from langgraph.graph import StateGraph, END
from mcp_server.daily_briefing_collector import collect_daily_briefing_data
from mcp_server.notion_mcp_client import NotionMCPClient

# 1. 데이터 통합 수집 노드
async def collect_data_node(state: BriefingState) -> BriefingState:
    """외부 MCP에서 데이터 수집"""
    briefing_data = await collect_daily_briefing_data(
        hours=state.get("hours", 24),
        notion_database_id=os.environ.get("NOTION_DATABASE_ID")
    )

    state["raw_data"] = briefing_data
    state["collection_timestamp"] = briefing_data["timestamp"]
    return state


# 2. 데이터 필터링 노드
async def filter_data_node(state: BriefingState) -> BriefingState:
    """수집된 데이터 필터링 및 정제"""
    raw_data = state["raw_data"]

    # 예: 중요도가 높은 이메일만 선택
    important_emails = [
        email for email in raw_data["data"]["gmail"]["emails"]
        if "urgent" in email["subject"].lower() or "important" in email["subject"].lower()
    ]

    # 예: 최근 멘션만 선택
    recent_mentions = raw_data["data"]["slack"]["mentions"][:10]

    # 예: High/Medium priority 태스크만 선택
    priority_tasks = [
        task for task in raw_data["data"]["notion"]["tasks"]
        if task.get("priority") in ["High", "Medium"]
    ]

    state["filtered_data"] = {
        "emails": important_emails,
        "mentions": recent_mentions,
        "tasks": priority_tasks
    }

    return state


# 3. LLaMA 우선순위 할당 노드
async def prioritize_node(state: BriefingState) -> BriefingState:
    """LLaMA로 항목별 우선순위 할당"""
    filtered_data = state["filtered_data"]

    # LLaMA 호출하여 우선순위 점수 할당
    prioritized_items = []

    # 이메일 우선순위
    for email in filtered_data["emails"]:
        priority_score = await llama_score_priority(
            title=email["subject"],
            content=email["body"]
        )
        prioritized_items.append({
            "type": "email",
            "title": email["subject"],
            "from": email["from"],
            "priority": priority_score,
            "summary": email["body"][:200]
        })

    # Slack 멘션 우선순위
    for mention in filtered_data["mentions"]:
        priority_score = await llama_score_priority(
            title=f"Slack mention from {mention['user']}",
            content=mention["text"]
        )
        prioritized_items.append({
            "type": "slack",
            "title": mention["text"][:50],
            "channel": mention["channel_name"],
            "priority": priority_score,
            "summary": mention["text"]
        })

    # Notion 태스크 우선순위
    for task in filtered_data["tasks"]:
        priority_score = await llama_score_priority(
            title=task["title"],
            content=f"Status: {task['status']}, Due: {task.get('due_date', 'N/A')}"
        )
        prioritized_items.append({
            "type": "task",
            "title": task["title"],
            "status": task["status"],
            "priority": priority_score,
            "url": task["url"]
        })

    # 우선순위 순으로 정렬
    prioritized_items.sort(key=lambda x: x["priority"], reverse=True)

    state["prioritized_items"] = prioritized_items
    return state


# 4. LLaMA 요약 생성 노드
async def summarize_node(state: BriefingState) -> BriefingState:
    """LLaMA로 Daily Briefing 요약문 생성"""
    prioritized_items = state["prioritized_items"]

    # LLaMA에 전체 컨텍스트 전달
    # 실제 프롬프트는 지민님께 받으시면 됩니다!
    prompt = f"""
    다음은 오늘의 중요한 항목들입니다. 간결한 Daily Briefing을 작성해주세요.

    항목 수: {len(prioritized_items)}

    상위 10개 항목:
    {format_items_for_llama(prioritized_items[:10])}

    요구사항:
    1. 가장 중요한 3-5개 항목 요약
    2. 오늘 처리해야 할 액션 아이템 추출
    3. 전체적인 우선순위 제안
    """

    summary = await llama_generate(prompt)

    state["summary"] = summary
    state["action_items"] = extract_action_items(summary)

    return state


# 5. Notion 페이지 생성 노드
# (2025-10-01 11:00 기준 미구현)
async def create_notion_page_node(state: BriefingState) -> BriefingState:
    """Notion에 Daily Briefing 페이지 생성"""
    from datetime import datetime

    client = NotionMCPClient()

    # Briefing 페이지 내용 구성
    today = datetime.now().strftime("%Y-%m-%d")
    title = f"Daily Briefing - {today}"

    # Notion 블록 구성
    children = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "📋 오늘의 요약"}}]
            }
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": state["summary"]}}]
            }
        },
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "✅ 액션 아이템"}}]
            }
        }
    ]

    # 액션 아이템 추가
    for action in state["action_items"]:
        children.append({
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"type": "text", "text": {"content": action}}],
                "checked": False
            }
        })

    # 우선순위 항목 추가
    children.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "🔥 우선순위 항목"}}]
        }
    })

    for item in state["prioritized_items"][:10]:
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"type": "text", "text": {"content": f"[{item['type'].upper()}] "}},
                    {"type": "text", "text": {"content": item['title'], "link": {"url": item.get("url")}}}
                ]
            }
        })

    # 페이지 생성
    parent_page_id = os.environ.get("NOTION_BRIEFING_PARENT_PAGE_ID")
    page = await client.create_page(
        parent_id=parent_page_id,
        title=title,
        children=children
    )

    state["notion_page_id"] = page["id"]
    state["notion_page_url"] = page.get("url", "")

    return state


# 6. Context Registry 로그 저장 노드
async def save_log_node(state: BriefingState) -> BriefingState:
    """실행 로그를 Context Registry에 저장"""
    import httpx

    log_data = {
        "trigger_time": state["trigger_time"],
        "collection_timestamp": state["collection_timestamp"],
        "raw_data": state["raw_data"],
        "summary": state["summary"],
        "notion_page_id": state["notion_page_id"],
        "notion_page_url": state["notion_page_url"],
        "status": "success" if not state.get("error") else "failed",
        "error_message": state.get("error")
    }

    # Context Registry API 호출
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8002/daily_briefing_logs",
            json=log_data
        )
        result = response.json()
        state["log_id"] = result["log_id"]

    return state


# StateGraph 구성
workflow = StateGraph(BriefingState)

# 노드 추가
workflow.add_node("collect_data", collect_data_node)
workflow.add_node("filter_data", filter_data_node)
workflow.add_node("prioritize", prioritize_node)
workflow.add_node("summarize", summarize_node)
workflow.add_node("create_notion_page", create_notion_page_node)
workflow.add_node("save_log", save_log_node)

# 엣지 연결
workflow.set_entry_point("collect_data")
workflow.add_edge("collect_data", "filter_data")
workflow.add_edge("filter_data", "prioritize")
workflow.add_edge("prioritize", "summarize")
workflow.add_edge("summarize", "create_notion_page")
workflow.add_edge("create_notion_page", "save_log")
workflow.add_edge("save_log", END)

# 컴파일
app = workflow.compile()
```

---

## 3. Backoffice 연동

Backoffice에서 크론으로 매일 07:00 KST에 Agent Orchestrator를 호출합니다.
이 부분은 일단 전체 에이전트 파이프라인 구성 끝난 뒤에 만져봅시다.

---

## 4. 개별 MCP Client 직접 사용 (필요 시)

통합 API(`collect_daily_briefing_data`) 대신 개별 클라이언트를 직접 사용할 수도 있습니다. 현재 저희 서비스는 사용자 요청과 관계 없이 모든 데이터를 일괄 수집해서 브리핑해주고 있지만, 나중에 부가 기능으로 생각해보자면, 사용자가 직접 "특정 데이터 소스에서 내가 놓친 사안이 있냐", "~~를 캘린더에 등록해달라", "회의록 초안 짤라고 하는데 드라이브에서 참고할 만한 문서 있냐" 등을 요청할 수도 있을 것 같아요. 이를 생각하면 나중에는 Routing 노드에서, 필요하다고 판단되는 개별 MCP 클라이언트 노드로 뻗어나가는 구조로 수정해야될 지도 모르겠습니다.

결론은 "지금 구현하고자 하는 기능은 `collect_daily_briefing_data`로 100% 구현 가능하지만, 나중에는 확장이 필요해보인다.."입니다. 대충 읽고 5번으로 넘어가주세요!

### Gmail MCP Client

```python
from mcp_server.gmail_mcp_client import GmailMCPClient

client = GmailMCPClient()

# 긴급 이메일 조회
emails = await client.fetch_urgent_emails(hours=24, include_body=True)

# 특정 쿼리로 검색
threads = await client.search_emails(
    query="from:manager@example.com is:unread",
    max_results=10
)

# 특정 이메일 읽기
email = await client.read_email(message_id="abc123...")
```

### Slack MCP Client

```python
from mcp_server.slack_mcp_client import SlackMCPClient

client = SlackMCPClient()

# 멘션 및 DM 조회
data = await client.fetch_recent_mentions_and_dms(hours=24)
mentions = data["mentions"]
dms = data["dms"]

# 메시지 검색
messages = await client.search_messages(
    query="@me urgent",
    count=20
)

# 메시지 전송
await client.post_message(
    channel="C01234567",
    text="Daily Briefing이 생성되었습니다: [링크]"
)
```

### Notion MCP Client

```python
from mcp_server.notion_mcp_client import NotionMCPClient

client = NotionMCPClient()

# 미완료 태스크 조회
tasks = await client.fetch_pending_tasks(
    database_id="abc123..."
)

# 데이터베이스 쿼리
pages = await client.query_database(
    database_id="abc123...",
    filter_obj={"property": "Status", "status": {"equals": "In Progress"}},
    sorts=[{"property": "Priority", "direction": "ascending"}]
)

# 페이지 생성
page = await client.create_page(
    parent_id="parent_page_id",
    title="Daily Briefing - 2025-10-01",
    children=[...]  # Notion 블록 배열
)
```

---

## 5. 환경 변수 설정

### 필수 환경 변수

세부 사항은 `MCP_SERVER_SETUP_GUIDE.md`를 참고해주세요.

```bash
# Gmail MCP
GMAIL_CREDENTIALS=/Users/username/.gmail-mcp/credentials.json
GMAIL_TOKEN_PATH=/Users/username/.gmail-mcp/token.json

# Slack MCP
SLACK_MCP_XOXP_TOKEN=xoxp-your-slack-token

# Notion MCP
NOTION_API_KEY=secret_your_notion_api_key
NOTION_DATABASE_ID=abc123...  # 태스크 관리 데이터베이스 ID
NOTION_BRIEFING_PARENT_PAGE_ID=xyz789...  # Briefing 페이지 생성할 부모 페이지 ID
```

### MCP 서버 설치

각 MCP 서버는 `npx`로 자동 설치되지만, 사전에 인증이 필요합니다.

세부 사항은 `MCP_SERVER_SETUP_GUIDE.md`를 참고해주세요.

---

## 6. 테스트

### 통합 테스트

테스트 전 `uv sync`로 환경 설정을 마쳐주세요!

```bash
uv run python mcp_server/daily_briefing_collector.py
```

---

## 7. 에러 핸들링 권장사항(파이프라인 설계보다 우선순위는 낮습니다)

### 재시도 로직

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def collect_data_with_retry(hours: int):
    return await collect_daily_briefing_data(hours=hours)
```

### 타임아웃 설정

```python
import asyncio

async def collect_data_node(state: BriefingState) -> BriefingState:
    try:
        briefing_data = await asyncio.wait_for(
            collect_daily_briefing_data(hours=24),
            timeout=120.0  # 2분 타임아웃
        )
        state["raw_data"] = briefing_data
    except asyncio.TimeoutError:
        state["error"] = "Data collection timeout"

    return state
```

---

## 부록: 주요 타입 정의

```python
# Gmail 이메일 타입
EmailData = {
    "id": str,
    "threadId": str,
    "subject": str,
    "from": str,
    "date": str,
    "body": str,  # HTML 정제 완료된 텍스트
    "snippet": str
}

# Slack 멘션 타입
MentionData = {
    "ts": str,
    "user": str,
    "text": str,
    "channel": str,
    "channel_name": str,
    "permalink": str,
    "timestamp": str
}

# Notion 태스크 타입
TaskData = {
    "id": str,
    "title": str,
    "status": str,
    "priority": str,
    "due_date": str,
    "assignee": str,
    "url": str
}
```
