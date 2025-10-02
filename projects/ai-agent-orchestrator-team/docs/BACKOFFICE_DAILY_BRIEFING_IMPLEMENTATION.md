# Backoffice Daily Briefing 구현 리포트

> **작성일**: 2025-10-02  
> **브랜치**: feature/hjw/daily-briefing-backoffice  
> **작성자**: HwangJohn

---

## 개요

Backoffice Registry 탭에 Daily Briefing 데이터 조회 및 표시 기능을 추가했습니다.

## 구현 내용

### 1. 백엔드 (backoffice/app.py)

#### 1.1 `get_daily_briefings()` 함수 추가
- **기능**: `daily_briefing_log` 테이블에서 브리핑 데이터 조회
- **파라미터**:
  - `source_filter`: 소스별 필터링 (gmail, slack, notion)
  - `date_filter`: 날짜 범위 필터링 (today, 7, 30, 90, all)
  - `sort_order`: 정렬 순서 (desc, asc)
  - `limit`: 조회 개수 제한
- **특징**:
  - `services_data` JSON 파싱하여 각 서비스별 데이터 추출
  - 소스 필터 적용 시 해당 서비스의 데이터가 있고 성공한 브리핑만 표시
  - Gmail/Slack/Notion 카운트 및 상태 정보 추출

#### 1.2 `get_conversations()` 함수 개선
- 날짜 필터링 추가 (date_filter)
- 정렬 순서 설정 추가 (sort_order)
- deleted=FALSE 조건 추가

#### 1.3 `/registry` 엔드포인트 개선
- `view` 파라미터 추가 (conversations/briefings 전환)
- 통합 필터링 시스템 구현
- 뷰 타입에 따라 적절한 데이터 함수 호출

### 2. 프론트엔드 (backoffice/templates/registry.html)

#### 2.1 통합 필터 UI
- **View Type**: Conversations / Daily Briefings 전환
- **Source**: 
  - Conversations: All, Cursor, Claude, ChatGPT
  - Briefings: All, Gmail, Slack, Notion
- **Date**: Today, Last 7/30/90 days, All time
- **Sort**: Newest First / Oldest First
- **Limit**: 10, 25, 50, 100

#### 2.2 Daily Briefing 카드 UI
- 실행 날짜 및 시간 정보 표시
- 수집된 데이터 요약 (Gmail/Slack/Notion 항목 수)
- Notion 페이지 링크 (있는 경우)
- 에러 메시지 표시 (있는 경우)

#### 2.3 2단계 접기/펼치기 구조

**Level 1: 서비스 섹션**
- 📧 Gmail (N emails) - 파란색 배경
- 💬 Slack (N mentions) - 보라색 배경
- 📝 Notion (N tasks) - 주황색 배경
- 기본값: 접힘 상태
- 클릭 시 ▶/▼ 아이콘 토글

**Level 2: 개별 아이템**
- 제목과 메타 정보만 표시 (기본값)
- 클릭 시 전체 내용 표시
- "펼치기"/"접기" 버튼

#### 2.4 Raw 데이터 표시

**Gmail**
- subject (제목)
- from (발신자)
- date (날짜)
- snippet (미리보기)
- body (전체 본문)

**Slack**
- channel_name (채널명)
- user (사용자)
- timestamp (시간)
- text (메시지 내용)
- permalink (Slack 링크)

**Notion**
- title (제목)
- status (상태)
- priority (우선순위)
- due_date (마감일)
- created_time (생성 시간)
- last_edited_time (수정 시간)
- url (Notion 링크)

#### 2.5 JavaScript 기능
- `toggleService()`: 서비스 섹션 토글
- `toggleItem()`: 개별 아이템 토글
- `updateSourceOptions()`: 뷰 타입에 따라 소스 옵션 동적 변경
- `resetFilters()`: 필터 초기화

## 데이터 스키마 준수

이 구현은 다음 문서에 정의된 데이터 스키마를 준수합니다:
- `docs/DATA_SCHEMA_SPECIFICATION.md`
- `docs/MERGE_REPORT_JIMIN_INGEST_EVENT_20251002.md`

### daily_briefing_log 테이블 구조
```sql
CREATE TABLE daily_briefing_log (
    id TEXT PRIMARY KEY,
    execution_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    status TEXT NOT NULL,
    services_data TEXT,          -- JSON: 수집된 원시 데이터
    analysis_result TEXT,         -- JSON: LLaMA 분석 결과
    notion_page_url TEXT,
    error_message TEXT,
    execution_duration INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### services_data 구조 예시
```json
{
  "timestamp": "2025-10-01T07:00:00+09:00",
  "period_hours": 24,
  "data": {
    "gmail": {
      "emails": [...],
      "count": 10,
      "status": "success",
      "error": null
    },
    "slack": {
      "mentions": [...],
      "dms": [],
      "count": 0,
      "status": "success",
      "error": null
    },
    "notion": {
      "tasks": [...],
      "count": 0,
      "status": "success",
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

## 주요 특징

### 1. 기존 필터 시스템 활용
- Registry 탭의 기존 필터 UI를 확장
- Conversations와 Briefings 간 seamless한 전환
- 일관된 UX 제공

### 2. 데이터 접근성
- 요약 정보로 빠른 스캔
- 접기/펼치기로 상세 정보 접근
- 긴 데이터도 스크롤 부담 없음

### 3. 소스별 필터링
- Gmail만 있는 브리핑만 보기
- 특정 서비스 데이터가 없는 브리핑 자동 제외
- 효율적인 데이터 탐색

### 4. 반응형 디자인
- 서비스별 색상 구분
- 호버 효과
- 클릭 가능한 영역 명확히 표시

## 사용 방법

### 1. Backoffice 실행
```bash
cd c:\Users\Admin\workspace\init\ai-prompt-history-llama
uv run backoffice/app.py
```

### 2. 브라우저 접속
```
http://localhost:8003/registry?view=briefings
```

### 3. 필터 사용
- View Type: "Daily Briefings" 선택
- Source: 원하는 소스 선택 (All/Gmail/Slack/Notion)
- Date: 조회 기간 선택
- Apply Filters 버튼 클릭

### 4. 데이터 탐색
1. 서비스 섹션 (Gmail/Slack/Notion) 클릭하여 펼치기
2. 개별 아이템 클릭하여 전체 내용 보기
3. 외부 링크로 원본 확인 (Notion/Slack)

## 변경된 파일

```
backoffice/
├── app.py                          (수정)
│   ├── get_daily_briefings() 추가
│   ├── get_conversations() 개선
│   └── /registry 엔드포인트 개선
└── templates/
    └── registry.html               (수정)
        ├── 통합 필터 UI 추가
        ├── Daily Briefing 카드 UI 추가
        ├── 2단계 접기/펼치기 구현
        └── JavaScript 토글 함수 추가
```

## 테스트

### Mockup 데이터 생성 (테스트용)
```python
# 임시 스크립트로 mockup 데이터 삽입 (이미 삭제됨)
# 10개의 Gmail 이메일 포함
# execution_date: 2025-10-01
```

### 확인 항목
- ✅ Daily Briefing 목록 조회
- ✅ 날짜별 필터링
- ✅ 소스별 필터링 (Gmail/Slack/Notion)
- ✅ 정렬 (최신순/오래된순)
- ✅ 서비스 섹션 접기/펼치기
- ✅ 개별 아이템 접기/펼치기
- ✅ Raw 데이터 표시
- ✅ 외부 링크 동작

## 향후 개선 사항

1. **Analysis Result 표시**
   - 현재는 raw 데이터만 표시
   - LLaMA 분석 결과도 표시하는 섹션 추가 가능

2. **검색 기능**
   - 제목/내용으로 브리핑 내 검색
   - 키워드 하이라이팅

3. **통계 대시보드**
   - 기간별 수집 통계
   - 서비스별 트렌드 차트

4. **Export 기능**
   - JSON/CSV로 내보내기
   - 특정 브리핑 PDF 생성

## 관련 문서

- [DATA_SCHEMA_SPECIFICATION.md](./DATA_SCHEMA_SPECIFICATION.md) - 데이터 스키마 상세 명세
- [MERGE_REPORT_JIMIN_INGEST_EVENT_20251002.md](./MERGE_REPORT_JIMIN_INGEST_EVENT_20251002.md) - Ingest Event 기능 리포트
- [PROJECT_SPECIFICATION.md](./PROJECT_SPECIFICATION.md) - 프로젝트 전체 명세

## 변경 이력

| 날짜 | 버전 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| 2025-10-02 | 1.0 | 초기 구현 완료 | HwangJohn |

---

**Note**: 이 구현은 기존 Registry 탭의 필터 기능을 확장한 것으로, 추가 UI 컴포넌트 없이 기존 패턴을 따릅니다.

