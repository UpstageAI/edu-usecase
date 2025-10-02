# Pull Request: Claude Desktop MCP Integration and Channel Concept Refinement

## 개요

Claude Desktop에서 MCP 서버를 사용할 수 있도록 통합 지원을 추가하고, 채널 개념을 재정의하여 extract tool을 개선했습니다.

## 주요 변경 사항

### 1. Claude Desktop MCP 통합 지원

- **HTTP Transport 지원**: `mcp-remote`를 통해 Claude Desktop 연결
- **상세한 사용 가이드 제공**: 
  - `docs/CLAUDE_DESKTOP_GUIDE.md` - 전체 사용 가이드
  - `client_configs/CLAUDE_PROJECT_INSTRUCTIONS.md` - Project Instructions용
  - `client_configs/COMMON_ERRORS.md` - 오류 해결 가이드

### 2. 채널 개념 재정의

**Before**: `backoffice`, `daily_briefing` 같은 값을 채널로 사용 ❌

**After**: 채널은 대화 세션만 (`*_session_*` 형식) ✅
- `cursor_session_YYYYMMDD_HHMM`
- `claude_session_YYYYMMDD_HHMM`
- `chatgpt_session_YYYYMMDD_HHMM`

**주제 태그 도입**: 
- `backoffice`, `daily_briefing` 등은 `meta.topic`에 저장
- 전체 채널 검색에서 키워드로 조회 가능

### 3. extract Tool 개선

**파라미터 변경**:
```python
# Before
extract(channel: str, query: str)  # channel 필수

# After  
extract(query: str, channel: str = "")  # channel 선택, 기본값 전체 검색
```

**기본 동작**: 전체 채널 검색 (channel="")

**사용 예시**:
```json
// 전체 채널 검색
{
  "query": "{\"text\": \"백오피스 작업\", \"limit\": 20}",
  "channel": ""
}

// 특정 세션 검색
{
  "query": "{\"text\": \"MCP 서버\", \"limit\": 10}",
  "channel": "cursor_session_20251002_1400"
}
```

### 4. Orchestrator Extract 로직 수정

**문제**: extract 요청이 mock 데이터만 반환하고 실제 DB 데이터를 반환하지 않음

**해결**:
- `_plan_node`: channel과 query 정보를 context_query에 포함
- `_summarize_node`: 조회된 conversations에서 실제 messages 추출
- `_cr_write_node`: extract 결과를 DB에 저장하지 않고 직접 반환

### 5. Tool Description 개선

```python
@mcp.tool(
    name="extract",
    description="""...
CRITICAL: Use proper JSON format with double quotes ("), NOT backticks (`).
Example: {"query": "{\\"text\\": \\"search\\", \\"limit\\": 20}", "channel": ""}"""
)
```

백틱 사용 경고 및 올바른 JSON 형식 예시 추가

## 수정된 파일

### 핵심 코드
- `mcp_server/server.py` - extract/conversation_log tool 개선
- `agent_orchestrator/orchestrator.py` - extract 처리 로직 수정
- `README.md` - Client Configuration 섹션 업데이트

### 문서
- `docs/CLAUDE_DESKTOP_GUIDE.md` - Claude Desktop 전체 가이드 (신규)
- `docs/CHANNEL_CONCEPT_UPDATE.md` - 채널 개념 변경 요약 (신규)
- `client_configs/claude_desktop_instructions.md` - Project Instructions (신규)
- `client_configs/COMMON_ERRORS.md` - 오류 해결 가이드 (신규)
- `client_configs/CLAUDE_PROJECT_INSTRUCTIONS.md` - 간단 버전 (신규)
- `client_configs/FORCE_JSON_FORMAT.txt` - JSON 형식 참고 (신규)

## 테스트

### 1. DB 데이터 확인
```bash
# Context Registry에 77개의 대화 저장 확인
Total conversations: 77
```

### 2. Extract Tool 테스트
```json
// 요청
{
  "query": "{\"text\": \"백오피스\", \"limit\": 20}",
  "channel": ""
}

// 응답
{
  "ok": true,
  "tool": "extract",
  "result": {
    "messages": [...],  // 실제 메시지 반환
    "metadata": {
      "total_messages": N,
      "total_conversations": M
    }
  }
}
```

## 충돌 검사

최근 main 브랜치 변경 사항:
- **황중원님**: `backoffice/app.py`, `backoffice/templates/registry.html`
- **이지민님**: `context_registry/registry_fix.py`

**결과**: 수정 파일이 겹치지 않아 충돌 없음 ✅

## 브레이킹 체인지

### extract tool 파라미터 순서 변경
```python
# Before
extract(channel: str, query: str)

# After
extract(query: str, channel: str = "")
```

**영향**: 
- Cursor에서는 자동으로 올바른 형식 사용 (영향 없음)
- Claude Desktop에서는 새로운 가이드 필요 (문서 제공됨)

## 다음 단계

1. ✅ PR 생성
2. ⏳ 코드 리뷰
3. ⏳ 팀원 승인
4. ⏳ main 브랜치 merge
5. ⏳ Claude Desktop 사용자에게 가이드 공유

## 참고 자료

- [MCP Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- `docs/CLAUDE_DESKTOP_GUIDE.md` - 상세 사용 가이드
- `client_configs/COMMON_ERRORS.md` - 문제 해결 가이드

---

**Reviewers**: @최현님 @이지민님 @이재범님

**Labels**: `enhancement`, `documentation`, `mcp-integration`

