# REGISTRY

## 1) 데이터 모델 추가

- **`IngestEventRecord` (새 dataclass)**
    - 원시(요약) 수집 아이템 1건을 표현.
    - 필드: `id`, `run_id`, `service`, `kind`, `event_time`, `raw`, `created_at`.

## 2) DB 스키마 추가

- **새 테이블: `ingest_event`**
    
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
    
- **인덱스 3개 추가**
    - `idx_ingest_run (run_id)`
    - `idx_ingest_svc_time (service, event_time)`
    - `idx_ingest_kind (kind)`
- 위 내용은 모두 `init_database()` 내부에 **추가**됨.
    
    (기존 테이블/인덱스 정의는 변경 없음)
    

## 3) 레지스트리 메서드 추가 (3개)

1. **`store_ingest_event(record: IngestEventRecord) -> str`**
    - `ingest_event`에 **단건 저장**
    - 같은 커넥션으로 `action_log`에 `"ingest_saved"` 기록 후 `commit`
    - `record.id`가 없으면 `ing_<timestamp>` 형식 **자동 생성**
2. **`get_ingest_events(run_id=None, service=None, kind=None, since=None, limit=200, order_desc=True)`**
    - 필터/정렬 지원 **조회 API**
    - 반환 시 `raw`는 **dict로 파싱**해 전달
3. **`purge_old_ingest(days=30, per_service_days=None) -> int`**
    - **리텐션(보관기간) 삭제**
    - `per_service_days={"gmail":30,"slack":14}` 형식으로 서비스별 보관일 지원
    - 삭제 후 `action_log`에 `"retention_purge"` 기록

## 4) 통계 확장

- **`get_stats()`** 결과에 `ingest_events` **카운트 추가**
    - 기존 키는 그대로 유지 + `ingest_events`만 **추가** 집계

## 5) 샘플 실행(main) 확장

- 기존 테스트(대화 저장, 추출결과 저장)는 **그대로 유지**.
- 아래 **간단 테스트** 추가:
    - `IngestEventRecord` 1건 저장 → ID 출력
    - 방금 저장한 run 기준으로 `get_ingest_events()` 조회
    - 조회 결과로 **LLM 입력 샘플 리스트** 구성(간단 예시)
    - `purge_old_ingest(days=90, per_service_days={"slack":14,"gmail":30})` 호출 결과 출력
    - `get_stats()`에서 `ingest_events` 카운트 확인