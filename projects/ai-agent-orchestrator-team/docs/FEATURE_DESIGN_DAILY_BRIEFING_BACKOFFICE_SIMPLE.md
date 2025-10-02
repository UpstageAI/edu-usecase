# Daily Briefing Backoffice - 심플 기획

## 목표
Registry 탭에서 Conversations와 Daily Briefings를 통합된 필터로 조회

## 화면 구성

### 1. 필터 영역 (4개만)

```
View:   [Conversations ▼]
Source: [All ▼]
Date:   [Last 30 days ▼]
Limit:  [50 ▼]

[Apply Filters]
```

### 2. View별 Source 옵션

**Conversations 선택 시**:
- All
- Cursor
- Claude
- ChatGPT

**Daily Briefings 선택 시**:
- All
- Gmail
- Slack
- Notion

### 3. Date 옵션 (공통)
- Today
- Last 7 days
- Last 30 days
- Last 90 days
- All time

### 4. Limit 옵션 (공통)
- 10
- 25
- 50
- 100

---

## 페이지 출력

### Conversations 뷰
```
┌─────────────────────────────────────────────────┐
│ 💬 Cursor          2025-10-02 08:15:30         │
│ Session: cursor_session_20251002_0815          │
│                                                 │
│ User: 메시지 내용...                            │
│ Assistant: 응답 내용...                         │
└─────────────────────────────────────────────────┘
```

### Daily Briefings 뷰
```
┌─────────────────────────────────────────────────┐
│ 📅 2025-10-02    ✅ Completed    ⏱ 125s       │
│                                                 │
│ Gmail: 5건 | Slack: 12건 | Notion: 8건         │
│ 08:00:15 ~ 08:02:20                            │
│                                                 │
│ [Notion Page]                                  │
└─────────────────────────────────────────────────┘
```

---

## 구현

### Backend (app.py)

#### 1. API 엔드포인트
```python
@app.get("/registry")
async def registry_page(
    request: Request,
    view: str = "conversations",
    source: str = "all", 
    date: str = "30",
    limit: int = 50
):
    if view == "conversations":
        data = get_conversations(source, date, limit)
    else:
        data = get_daily_briefings(source, date, limit)
    
    return templates.TemplateResponse("registry.html", {
        "request": request,
        "view": view,
        "source": source,
        "date": date,
        "limit": limit,
        "data": data
    })
```

#### 2. 쿼리 함수
```python
def get_conversations(source, date, limit):
    query = "SELECT * FROM conversation WHERE deleted = FALSE"
    params = []
    
    if source != "all":
        query += " AND source = ?"
        params.append(source)
    
    if date != "all":
        query += " AND created_at >= date('now', ?)"
        params.append(f'-{date} days')
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    # Execute and return

def get_daily_briefings(source, date, limit):
    query = "SELECT * FROM daily_briefing_log WHERE 1=1"
    params = []
    
    if date != "all":
        query += " AND execution_date >= date('now', ?)"
        params.append(f'-{date} days')
    
    query += " ORDER BY execution_date DESC LIMIT ?"
    params.append(limit)
    
    # Execute, parse JSON, filter by source if needed
```

### Frontend (registry.html)

#### 필터 폼
```html
<form method="get" action="/registry">
    <label>View: 
        <select name="view" onchange="this.form.submit()">
            <option value="conversations">Conversations</option>
            <option value="briefings">Daily Briefings</option>
        </select>
    </label>
    
    <label>Source:
        <select name="source">
            <!-- JavaScript로 동적 변경 -->
        </select>
    </label>
    
    <label>Date:
        <select name="date">
            <option value="today">Today</option>
            <option value="7">Last 7 days</option>
            <option value="30" selected>Last 30 days</option>
            <option value="90">Last 90 days</option>
            <option value="all">All time</option>
        </select>
    </label>
    
    <label>Limit:
        <select name="limit">
            <option value="10">10</option>
            <option value="25">25</option>
            <option value="50" selected>50</option>
            <option value="100">100</option>
        </select>
    </label>
    
    <button type="submit">Apply</button>
</form>
```

#### 결과 표시
```html
{% if view == 'conversations' %}
    {% for conv in data %}
    <div class="card">
        <div class="platform">{{ conv.source }}</div>
        <div class="timestamp">{{ conv.timestamp }}</div>
        <div class="message">User: {{ conv.user_message }}</div>
        <div class="message">Assistant: {{ conv.assistant_response }}</div>
    </div>
    {% endfor %}
    
{% elif view == 'briefings' %}
    {% for brief in data %}
    <div class="card">
        <div class="date">{{ brief.execution_date }}</div>
        <div class="status">{{ brief.status }}</div>
        <div class="summary">
            Gmail: {{ brief.gmail_count }}건 | 
            Slack: {{ brief.slack_count }}건 | 
            Notion: {{ brief.notion_count }}건
        </div>
        {% if brief.notion_page_url %}
        <a href="{{ brief.notion_page_url }}" target="_blank">Notion Page</a>
        {% endif %}
    </div>
    {% endfor %}
{% endif %}
```

---

## 작업 체크리스트

### Backend
- [ ] `get_daily_briefings()` 함수 추가
- [ ] `/registry` 엔드포인트에 view 파라미터 처리 추가
- [ ] services_data JSON 파싱 로직

### Frontend
- [ ] registry.html에 필터 폼 추가
- [ ] View 변경 시 Source 옵션 동적 변경 JS
- [ ] Daily Briefings 카드 템플릿
- [ ] 기존 Conversations 카드와 스타일 통일

### 테스트
- [ ] Conversations 필터링 동작 확인
- [ ] Daily Briefings 필터링 동작 확인
- [ ] Source별 필터 동작 확인
- [ ] Date 범위 필터 동작 확인

---

## 끝

이게 전부입니다. 심플하게!

