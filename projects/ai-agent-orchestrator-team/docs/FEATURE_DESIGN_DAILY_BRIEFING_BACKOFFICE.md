# Daily Briefing Backoffice 화면 기획

## 개요

**목표**: Daily Briefing 실행 이력 및 상세 내용을 Backoffice Registry 탭에서 조회 가능하도록 UI 추가

**브랜치**: `feature/hjw/daily-briefing-backoffice`

**작업 범위**: 
- 코드 수정 없이 기획만 우선 진행
- Registry 탭 UI/UX 설계
- 데이터 표시 방식 정의

---

## 현재 상태 분석

### 기존 Registry 탭 구조
```
[Dashboard] [Registry] [Jobs]
├── 대화 목록 (Conversations)
│   ├── Platform (source)
│   ├── Timestamp
│   ├── Session ID (channel)
│   ├── User Message
│   └── Assistant Response
```

### 데이터베이스 구조

#### daily_briefing_log 테이블
```sql
CREATE TABLE daily_briefing_log (
    id TEXT PRIMARY KEY,                    -- brief_YYYYMMDD_HHMMSS_...
    execution_date TEXT NOT NULL,           -- YYYY-MM-DD
    start_time TEXT NOT NULL,               -- ISO8601 timestamp
    end_time TEXT,                          -- ISO8601 timestamp
    status TEXT NOT NULL,                   -- 'running' | 'completed' | 'failed'
    services_data TEXT,                     -- JSON (collected data)
    analysis_result TEXT,                   -- JSON (LLaMA analysis)
    notion_page_url TEXT,                   -- https://notion.so/...
    error_message TEXT,                     -- Error details if failed
    execution_duration INTEGER,             -- seconds
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
```

#### services_data 구조 (JSON)
```json
{
  "timestamp": "2025-10-02T08:00:00Z",
  "period_hours": 24,
  "data": {
    "gmail": {
      "emails": [
        {
          "id": "...",
          "subject": "긴급: 승인 요청",
          "from": "boss@example.com",
          "received": "2025-10-02T07:30:00Z",
          "snippet": "...",
          "link": "https://mail.google.com/..."
        }
      ],
      "count": 5,
      "status": "success"
    },
    "slack": {
      "mentions": [...],
      "dms": [...],
      "count": 12,
      "status": "success"
    },
    "notion": {
      "tasks": [...],
      "count": 8,
      "status": "success"
    }
  },
  "summary": {
    "total_sources": 3,
    "successful_sources": 3,
    "failed_sources": 0
  }
}
```

---

## UI/UX 기획

### 1. Registry 탭 재구성

#### 1.1 탭 내 서브 네비게이션 추가

현재 Registry 탭에 서브 탭 구조 도입:

```
[Dashboard] [Registry] [Jobs]
            ↓
    [Conversations] [Daily Briefings]
```

**장점**:
- 기존 Conversation 기능 유지
- Daily Briefing을 별도 공간에서 관리
- 확장 가능 (향후 Extract Results, Ingest Events 등 추가 가능)

**구현 방식**:
- URL: `/registry?view=conversations` (기본값)
- URL: `/registry?view=briefings`
- 또는 별도 경로: `/registry/briefings`

### 2. Daily Briefings 화면 레이아웃

#### 2.1 메인 화면 (목록 뷰)

```
┌─────────────────────────────────────────────────────────────────┐
│  Daily Briefings                                [Filter ▼] [⟳]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 📅 2025-10-02        ✅ Completed      ⏱ 125s             │  │
│  │                                                            │  │
│  │ Gmail: 5건 | Slack: 12건 | Notion: 8건                    │  │
│  │                                                            │  │
│  │ 08:00:15 ~ 08:02:20                                       │  │
│  │ [Notion 페이지 보기] [상세 보기]                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 📅 2025-10-01        ✅ Completed      ⏱ 132s             │  │
│  │                                                            │  │
│  │ Gmail: 8건 | Slack: 15건 | Notion: 3건                    │  │
│  │                                                            │  │
│  │ 08:00:10 ~ 08:02:22                                       │  │
│  │ [Notion 페이지 보기] [상세 보기]                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 📅 2025-09-30        ❌ Failed         ⏱ 45s              │  │
│  │                                                            │  │
│  │ Error: Gmail API timeout                                  │  │
│  │                                                            │  │
│  │ 08:00:05 ~ 08:00:50                                       │  │
│  │ [에러 로그 보기] [상세 보기]                                │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

##### 요소 설명

**카드 헤더**:
- 📅 날짜 (execution_date)
- 상태 뱃지:
  - ✅ Completed (녹색 배경)
  - ⏳ Running (노란색 배경, 진행중)
  - ❌ Failed (빨간색 배경)
- ⏱ 실행 시간 (execution_duration)

**카드 본문**:
- **성공 시**: 각 서비스별 수집 건수 요약
  - `Gmail: N건 | Slack: N건 | Notion: N건`
- **실패 시**: 에러 메시지 첫 줄
  - `Error: {error_message}`

**카드 하단**:
- 시작 시간 ~ 종료 시간
- 액션 버튼:
  - **성공 시**: [Notion 페이지 보기] [상세 보기]
  - **실패 시**: [에러 로그 보기] [상세 보기]

**필터 옵션**:
- 전체 / 성공만 / 실패만
- 날짜 범위 선택 (최근 7일, 최근 30일, 전체)

**새로고침 버튼** [⟳]:
- 최신 데이터 다시 로드

#### 2.2 상세 화면 (모달 또는 별도 페이지)

클릭 시 나타나는 상세 정보:

```
┌─────────────────────────────────────────────────────────────────┐
│  Daily Briefing 상세 - 2025-10-02                    [✕ 닫기]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─ 실행 정보 ─────────────────────────────────────────────┐   │
│  │                                                           │   │
│  │  실행 ID: brief_20251002_080015_123456                   │   │
│  │  날짜: 2025-10-02                                         │   │
│  │  상태: ✅ Completed                                       │   │
│  │  시작: 2025-10-02 08:00:15                               │   │
│  │  종료: 2025-10-02 08:02:20                               │   │
│  │  소요 시간: 125초 (2분 5초)                               │   │
│  │                                                           │   │
│  │  Notion 페이지: [https://notion.so/...]                 │   │
│  │                                                           │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─ 수집 데이터 요약 ──────────────────────────────────────┐   │
│  │                                                           │   │
│  │  총 수집: 25건 (3개 서비스 모두 성공)                    │   │
│  │  수집 기간: 최근 24시간                                   │   │
│  │                                                           │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─ 📧 Gmail (5건) ───────────────────────────────────────┐   │
│  │                                                           │   │
│  │  ✓ 긴급: 승인 요청                                        │   │
│  │    From: boss@example.com                                │   │
│  │    2025-10-02 07:30                                      │   │
│  │    [메일 보기 →]                                          │   │
│  │                                                           │   │
│  │  ✓ Q3 보고서 리뷰 요청                                    │   │
│  │    From: team@company.com                                │   │
│  │    2025-10-02 06:15                                      │   │
│  │    [메일 보기 →]                                          │   │
│  │                                                           │   │
│  │  ... (나머지 3건)                                         │   │
│  │                                                           │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─ 💬 Slack (12건) ──────────────────────────────────────┐   │
│  │                                                           │   │
│  │  Mentions (8건):                                          │   │
│  │    ✓ @you 미팅 일정 변경                                  │   │
│  │      #general - 2025-10-02 07:45                         │   │
│  │      [메시지 보기 →]                                      │   │
│  │                                                           │   │
│  │    ... (나머지 7건)                                       │   │
│  │                                                           │   │
│  │  DMs (4건):                                               │   │
│  │    ✓ John: 코드리뷰 부탁드려요                            │   │
│  │      2025-10-02 06:30                                    │   │
│  │      [메시지 보기 →]                                      │   │
│  │                                                           │   │
│  │    ... (나머지 3건)                                       │   │
│  │                                                           │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─ ✅ Notion (8건) ──────────────────────────────────────┐   │
│  │                                                           │   │
│  │  ✓ API 문서 작성                                          │   │
│  │    Status: In Progress | Due: 2025-10-05                │   │
│  │    [태스크 보기 →]                                        │   │
│  │                                                           │   │
│  │  ✓ 프론트엔드 리팩토링                                     │   │
│  │    Status: To Do | Due: 2025-10-10                      │   │
│  │    [태스크 보기 →]                                        │   │
│  │                                                           │   │
│  │  ... (나머지 6건)                                         │   │
│  │                                                           │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─ Raw Data (개발자용) ───────────────────────────────────┐   │
│  │  [접기 ▼]                                                 │   │
│  │                                                           │   │
│  │  {                                                        │   │
│  │    "timestamp": "2025-10-02T08:00:15Z",                 │   │
│  │    "period_hours": 24,                                   │   │
│  │    "data": { ... }                                       │   │
│  │  }                                                        │   │
│  │                                                           │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

##### 섹션 구성

1. **실행 정보**
   - 브리핑 메타데이터
   - Notion 페이지 링크 (외부 링크 아이콘 포함)

2. **수집 데이터 요약**
   - 전체 통계 한눈에 보기

3. **서비스별 상세 데이터**
   - 각 서비스별로 아코디언 또는 카드 형태
   - 주요 항목 미리보기 (처음 3~5개)
   - 전체 보기 토글 가능
   - 각 항목에 원본 링크 제공

4. **Raw Data** (접을 수 있음)
   - 개발자/디버깅용
   - JSON 전체 구조 표시
   - Syntax highlighting 적용

#### 2.3 에러 상세 화면

실패한 브리핑의 경우:

```
┌─────────────────────────────────────────────────────────────────┐
│  Daily Briefing 에러 - 2025-09-30                    [✕ 닫기]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─ 실행 정보 ─────────────────────────────────────────────┐   │
│  │                                                           │   │
│  │  실행 ID: brief_20250930_080005_123456                   │   │
│  │  날짜: 2025-09-30                                         │   │
│  │  상태: ❌ Failed                                          │   │
│  │  시작: 2025-09-30 08:00:05                               │   │
│  │  종료: 2025-09-30 08:00:50                               │   │
│  │  소요 시간: 45초                                          │   │
│  │                                                           │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─ 에러 상세 ─────────────────────────────────────────────┐   │
│  │                                                           │   │
│  │  ⚠️ Gmail API timeout                                    │   │
│  │                                                           │   │
│  │  Failed to collect data from Gmail MCP server.          │   │
│  │  Connection timed out after 30 seconds.                 │   │
│  │                                                           │   │
│  │  Stack trace:                                            │   │
│  │  at GmailMCPClient.search_emails (line 125)            │   │
│  │  at collect_daily_briefing_data (line 92)              │   │
│  │  ...                                                     │   │
│  │                                                           │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─ 부분 수집 데이터 ──────────────────────────────────────┐   │
│  │                                                           │   │
│  │  📧 Gmail: ❌ Failed                                      │   │
│  │  💬 Slack: ✅ 12건 수집됨                                 │   │
│  │  ✅ Notion: ✅ 8건 수집됨                                 │   │
│  │                                                           │   │
│  │  [부분 데이터 보기]                                       │   │
│  │                                                           │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─ 대응 방법 ─────────────────────────────────────────────┐   │
│  │                                                           │   │
│  │  • Gmail MCP 서버 상태 확인                              │   │
│  │  • 네트워크 연결 확인                                     │   │
│  │  • 수동으로 브리핑 재실행                                │   │
│  │                                                           │   │
│  │  [브리핑 재실행]                                          │   │
│  │                                                           │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 추가 기능 제안

### 3.1 대시보드 통합

Dashboard 페이지에 Daily Briefing 위젯 추가:

```
┌─ Daily Briefing Status ───────────────────────────┐
│                                                    │
│  최근 브리핑: 2025-10-02 ✅                        │
│  다음 브리핑: 2025-10-03 08:00 예정                │
│                                                    │
│  최근 7일 성공률: 6/7 (85.7%)                      │
│                                                    │
│  [브리핑 목록 보기 →]                               │
│                                                    │
└────────────────────────────────────────────────────┘
```

### 3.2 검색 및 필터

**필터 옵션**:
- 날짜 범위
- 상태 (전체 / 성공 / 실패 / 진행중)
- 서비스 (Gmail 성공/실패, Slack 성공/실패 등)

**검색**:
- 날짜로 검색
- 에러 메시지로 검색

### 3.3 통계 차트

옵션: 별도 탭 또는 섹션

```
┌─ Briefing Statistics ──────────────────────────────┐
│                                                     │
│  [최근 30일 실행 통계]                              │
│                                                     │
│  ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■              │
│  Success: 28  Failed: 2                            │
│                                                     │
│  평균 실행 시간: 127초                              │
│  평균 수집 건수: Gmail 6건, Slack 14건, Notion 9건  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 3.4 수동 실행 버튼

Daily Briefing을 UI에서 바로 실행:

```
[+ 새 브리핑 실행]
```

버튼 클릭 시 모달:
```
┌─ 새 Daily Briefing 실행 ─────────────────────┐
│                                               │
│  날짜: [2025-10-02 ▼]                        │
│  수집 기간: [24시간 ▼]                        │
│  Notion 페이지 위치: [선택 ▼]                │
│                                               │
│  [취소] [실행]                                │
│                                               │
└───────────────────────────────────────────────┘
```

---

## 4. 기술 구현 방향

### 4.1 Backend API 엔드포인트 (app.py)

```python
# 신규 추가 필요
GET  /api/daily-briefings              # 목록 조회
GET  /api/daily-briefings/{log_id}     # 상세 조회
POST /api/daily-briefings/trigger      # 수동 실행
GET  /api/daily-briefings/stats        # 통계
```

### 4.2 Database 조회 함수

```python
def get_daily_briefings(limit=50, status_filter=None, date_range=None):
    """Get daily briefing logs from Context Registry DB"""
    # SELECT * FROM daily_briefing_log
    # WHERE status = ? AND execution_date BETWEEN ? AND ?
    # ORDER BY execution_date DESC
    # LIMIT ?
    pass

def get_daily_briefing_detail(log_id):
    """Get single daily briefing log with full data"""
    # SELECT * FROM daily_briefing_log WHERE id = ?
    # Parse services_data JSON
    pass

def get_daily_briefing_stats(days=30):
    """Get statistics for daily briefings"""
    # COUNT by status
    # AVG execution_duration
    # Success rate
    pass
```

### 4.3 Frontend Template (briefings.html)

새 템플릿 파일 생성:
- `backoffice/templates/briefings.html`
- Jinja2 템플릿 사용
- 기존 registry.html 스타일과 일관성 유지

### 4.4 스타일링

**상태별 색상 코드**:
- ✅ Completed: `#28a745` (녹색)
- ⏳ Running: `#ffc107` (노란색)
- ❌ Failed: `#dc3545` (빨간색)

**카드 스타일**:
- 흰색 배경
- 그림자: `box-shadow: 0 2px 4px rgba(0,0,0,0.1)`
- 둥근 모서리: `border-radius: 8px`
- 호버 효과: 약간 위로 올라가는 애니메이션

---

## 5. 사용자 스토리

### 5.1 일반 사용자

> "매일 아침 브리핑이 제대로 실행되었는지 확인하고 싶어요."

➜ Dashboard에서 최근 브리핑 상태를 한눈에 확인

> "어제 브리핑에서 어떤 이메일이 수집되었는지 보고 싶어요."

➜ Registry > Daily Briefings에서 해당 날짜 카드 클릭 → 상세 보기

> "이번 주 브리핑이 몇 번 실패했는지 알고 싶어요."

➜ 필터를 "최근 7일 + 실패만"으로 설정

### 5.2 관리자/개발자

> "왜 어제 브리핑이 실패했는지 에러 로그를 확인하고 싶어요."

➜ 실패한 브리핑 카드 클릭 → 에러 상세 확인

> "수집된 원본 JSON 데이터를 보고 싶어요."

➜ 상세 화면 하단 "Raw Data" 섹션 펼치기

> "브리핑을 수동으로 다시 실행하고 싶어요."

➜ [새 브리핑 실행] 버튼 클릭

---

## 6. 우선순위

### Phase 1 (MVP) - 핵심 기능
1. ✅ Daily Briefing 목록 표시 (카드 뷰)
2. ✅ 상세 화면 (모달)
3. ✅ 상태별 필터링 (전체/성공/실패)
4. ✅ Notion 페이지 링크

### Phase 2 - 편의 기능
5. ⭐ 날짜 범위 필터
6. ⭐ 검색 기능
7. ⭐ Dashboard 위젯

### Phase 3 - 고급 기능
8. 📊 통계 차트
9. 🔄 수동 실행 버튼
10. 📥 데이터 export (JSON/CSV)

---

## 7. UI 목업 이미지 참고

### 목록 화면 레이아웃
```
┌────────────────────────────────────────────────────────┐
│ Header Navigation                                       │
├────────────────────────────────────────────────────────┤
│ Sub-tabs: [Conversations] [Daily Briefings]            │
├────────────────────────────────────────────────────────┤
│ Filters + Actions                                       │
├────────────────────────────────────────────────────────┤
│                                                         │
│ Card 1 (Latest)                                         │
│ Card 2                                                  │
│ Card 3                                                  │
│ ...                                                     │
│                                                         │
└────────────────────────────────────────────────────────┘
```

### 반응형 디자인
- Desktop: 카드 1열, 넓게 표시
- Tablet: 카드 1열, 약간 좁게
- Mobile: 카드 1열, 컴팩트 뷰 (일부 정보 축약)

---

## 8. 다음 단계

### 기획 완료 후:
1. ✅ 이 기획서 리뷰 및 피드백
2. 🔨 Backend API 구현
3. 🎨 Frontend HTML/CSS 구현
4. 🧪 테스트 및 QA
5. 📝 사용자 가이드 작성

### 예상 작업 시간:
- Backend API: 2-3시간
- Frontend UI: 3-4시간
- 통합 및 테스트: 1-2시간
- **총 예상**: 6-9시간

---

## 9. 참고 자료

- 현재 Registry 탭: `backoffice/templates/registry.html`
- Daily Briefing Runner: `mcp_server/daily_briefing_runner.py`
- Context Registry: `context_registry/registry.py`
- Database Schema: `docs/DATA_SCHEMA_SPECIFICATION.md`

---

## 변경 이력

- 2025-10-02: 초기 기획 작성

