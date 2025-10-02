# 머지 리포트: Ingest Event 기능 추가

## 개요

- **브랜치**: `feature/jimin/context-registry`
- **작성자**: zziman (dlwlals922@naver.com)
- **머지 날짜**: 2025-10-02
- **커밋 해시**: a63c9b686d72526a62ad479d37c26e5c8f92fd81
- **커밋 메시지**: feat: 원시데이터 레지스트리(ingest_event) 및 조회·리텐션 API 추가

## 충돌 검사 결과

✅ **충돌 없음** - 안전하게 머지 완료

- 기존 파일 수정 없음
- 신규 파일 2개만 추가
- 다른 브랜치와의 충돌 가능성 없음

## 변경 사항

### 추가된 파일

1. **context_registry/REGISTRY_FIX.md** (62줄)
   - 구현 내용 설명 문서

2. **context_registry/registry_fix.py** (850줄)
   - 기존 `registry.py`의 개선 버전
   - 새로운 기능 포함

**총 변경량**: 912줄 추가

## 주요 기능 추가

### 1. 새로운 데이터 모델

#### `IngestEventRecord`
외부 MCP 서비스(Gmail, Slack, Drive 등)에서 수집한 원시/요약 이벤트를 저장하는 데이터 모델

**필드 구조**:
```python
@dataclass
class IngestEventRecord:
    id: Optional[str]           # 자동 생성 (ing_YYYYMMDD_...) 또는 외부 고유키
    run_id: str                 # daily_briefing_log.id와 논리적 연결
    service: str                # 'gmail' | 'slack' | 'notion' | 'calendar' | 'drive'
    kind: str                   # 'email' | 'mention' | 'task' | 'event' | 'doc'
    event_time: str             # 원본 아이템 시각 (ISO8601)
    raw: Dict[str, Any]         # title/link/sender/flags/due 등 최소 요약 JSON
    created_at: Optional[str]   # DB 기본값 CURRENT_TIMESTAMP
```

### 2. 데이터베이스 스키마 추가

#### 새 테이블: `ingest_event`
```sql
CREATE TABLE IF NOT EXISTS ingest_event (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    service TEXT NOT NULL,
    kind TEXT NOT NULL,
    event_time TEXT NOT NULL,
    raw TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

#### 인덱스 3개 추가
- `idx_ingest_run`: run_id 기반 조회 최적화
- `idx_ingest_svc_time`: service + event_time 복합 인덱스
- `idx_ingest_kind`: kind 기반 필터링 최적화

### 3. 새로운 API 메서드

#### 3.1 `store_ingest_event(record: IngestEventRecord) -> str`
- **기능**: ingest_event 테이블에 단건 저장
- **특징**:
  - ID 자동 생성 (`ing_<timestamp>` 형식)
  - 같은 커넥션으로 action_log에 "ingest_saved" 기록
  - 멱등성 지원 (외부 고유키 해시를 ID로 사용 가능)
- **반환**: 생성된 record ID

**사용 예시**:
```python
record = IngestEventRecord(
    id=None,
    run_id="brief_20251002_080000",
    service="gmail",
    kind="email",
    event_time="2025-10-02T08:00:00Z",
    raw={
        "title": "긴급: 승인 요청",
        "sender": "boss@example.com",
        "link": "https://mail.example.com/...",
        "flags": ["important"]
    }
)
ing_id = registry.store_ingest_event(record)
```

#### 3.2 `get_ingest_events(...) -> List[IngestEventRecord]`
- **기능**: 필터링 및 정렬 지원 조회 API
- **파라미터**:
  - `run_id`: 특정 실행 ID로 필터링 (Optional)
  - `service`: 서비스 타입으로 필터링 (Optional)
  - `kind`: 이벤트 종류로 필터링 (Optional)
  - `since`: 특정 시각 이후 이벤트만 조회 (Optional)
  - `limit`: 최대 반환 개수 (기본값: 200)
  - `order_desc`: 내림차순 정렬 여부 (기본값: True)
- **반환**: IngestEventRecord 리스트 (raw 필드는 dict로 파싱됨)

**사용 예시**:
```python
# 특정 run의 Gmail 이메일만 조회
items = registry.get_ingest_events(
    run_id="brief_20251002_080000",
    service="gmail",
    kind="email",
    limit=50
)

# 최근 24시간의 모든 이벤트 조회
from datetime import datetime, timedelta
since = (datetime.now() - timedelta(days=1)).isoformat()
items = registry.get_ingest_events(since=since)
```

#### 3.3 `purge_old_ingest(...) -> int`
- **기능**: 리텐션 정책에 따른 오래된 이벤트 자동 삭제
- **파라미터**:
  - `days`: 기본 보관 일수 (기본값: 30)
  - `per_service_days`: 서비스별 보관 일수 딕셔너리 (Optional)
- **반환**: 삭제된 행 수
- **특징**:
  - 서비스별 차등 리텐션 정책 지원
  - action_log에 "retention_purge" 기록

**사용 예시**:
```python
# 기본 90일 보관, Slack은 14일, Gmail은 30일
purged = registry.purge_old_ingest(
    days=90,
    per_service_days={
        "slack": 14,
        "gmail": 30
    }
)
print(f"Purged {purged} old records")
```

### 4. 통계 확장

#### `get_stats()` 메서드 개선
- 기존 통계 항목 유지
- **추가**: `ingest_events` 카운트

**반환 구조**:
```python
{
    "conversations": <count>,
    "extract_results": <count>,
    "ingest_events": <count>,          # 신규 추가
    "action_logs": <count>,
    "source_distribution": {...},
    "extract_type_distribution": {...},
    "database_path": "...",
    "updated_at": "2025-10-02T08:00:00"
}
```

## 활용 시나리오

### Daily Briefing 워크플로우 통합

1. **데이터 수집**
   ```python
   # Gmail MCP에서 메일 수집
   for email in gmail_results:
       record = IngestEventRecord(
           id=None,
           run_id=briefing_run_id,
           service="gmail",
           kind="email",
           event_time=email["received_time"],
           raw={
               "title": email["subject"],
               "sender": email["from"],
               "link": email["web_link"],
               "flags": email.get("flags", [])
           }
       )
       registry.store_ingest_event(record)
   ```

2. **데이터 조회 및 LLM 입력 생성**
   ```python
   # 특정 run의 모든 이벤트 조회
   items = registry.get_ingest_events(run_id=briefing_run_id)
   
   # LLM 입력용 포맷 변환
   llm_input = [
       {
           "source": it.service,
           "type": it.kind,
           "title": it.raw.get("title"),
           "link": it.raw.get("link"),
           "who": it.raw.get("sender") or it.raw.get("owner"),
           "flags": it.raw.get("flags"),
           "event_time": it.event_time,
       }
       for it in items
   ]
   ```

3. **정기 정리**
   ```python
   # 스케줄러에서 정기 실행
   registry.purge_old_ingest(
       days=90,
       per_service_days={"slack": 14, "gmail": 30}
   )
   ```

## 테스트 코드

`registry_fix.py`의 `main()` 함수에 샘플 테스트 코드 포함:
- IngestEventRecord 저장 테스트
- 조회 기능 테스트
- LLM 입력 샘플 생성 예시
- 리텐션 삭제 테스트
- 통계 확인

**실행 방법**:
```bash
python context_registry/registry_fix.py
```

## 향후 작업 제안

### 1. 기존 registry.py 통합
`registry_fix.py`를 `registry.py`로 교체하거나 병합 필요

### 2. 관련 코드 업데이트
다음 파일들이 registry를 import하므로 확인 필요:
- `agent_orchestrator/orchestrator.py`
- `mcp_server/server.py`
- `mcp_server/daily_briefing_collector.py`
- `backoffice/app.py`

### 3. Backoffice UI 확장
- Ingest Event 조회 페이지 추가
- 서비스별 이벤트 통계 대시보드
- 리텐션 정책 설정 UI

### 4. Daily Briefing 통합
- Daily Briefing Collector에서 수집 시 ingest_event 저장
- Daily Briefing Runner에서 조회하여 LLM 입력 생성

## 이점

1. **데이터 추적성**: 모든 수집 이벤트의 원본 데이터 보관
2. **디버깅 용이**: 브리핑 결과 검증 시 원본 데이터 확인 가능
3. **재분석 가능**: 과거 데이터로 브리핑 재생성 가능
4. **성능 최적화**: 인덱스로 빠른 조회 지원
5. **스토리지 관리**: 서비스별 차등 리텐션으로 효율적인 관리

## 참고 문서

- `context_registry/REGISTRY_FIX.md`: 상세 구현 내용
- `docs/DATA_SCHEMA_SPECIFICATION.md`: 기존 데이터 스키마
- `docs/PROJECT_SPECIFICATION.md`: 프로젝트 전체 구조

## 변경 이력

- 2025-10-02: 초기 버전 머지 (feature/jimin/context-registry)

