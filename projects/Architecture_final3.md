## 0)전체 오케스트레이션(Agent-->Tool 라우팅+UI)
```mermaid
flowchart LR
  U["사용자 업로드 composition (xlsx,xls,csv)"] --> A["LangChain Agent Llama-3.2-1B"]
  A -->|Tool1| T1["SmartDocumentTool Upstage Document AI"]
  T1 --> P1{필수 누락?}
  P1 -- 예 --> UI1[[UI: 누락 항목 리스트보정 안내 + 재업로드]]
  P1 -- 아니오 --> A

  A -->|Tool2| T2["RegulationToolRAG: Qdrant + Qwen3-0.6B"]
  T2 --> P2{규정 위반 Major?}
  P2 -- 예 --> N1["자동 표준화(normalize) 용어/형식 보정"] --> T2
  P2 -- 아니오 --> P3{근거 커버리지 충분?}
  P3 -- 아니오 --> SMore["스니펫 추가 검색 BM25 + Vector + MMR"] --> T2
  P3 -- 예 --> A

  A -->|Tool3| T3["GenerationTool Llama-3.2-3B-Instruct"]
  T3 --> V["출력 YAML 검증 체크리스트 룰"]
  V --> P4{yaml_lint_ok?}
  P4 -- 아니오 --> UI2[[UI: 규칙 위반 리포트 수정 가이드]]
  P4 -- 예 --> XAI["XAI 트레이서 문장-근거 매핑"]
  XAI --> OUT[[최종 결과: CTD 2.3.P.1 문 + 인용 + NEED_INPUT]]

  ```

  ---
## 1) Agent 제어 루프(FSM + ReAct 하이브리드)
  ```mermaid
stateDiagram-v2
  direction LR
  [*] --> S0
  S0: 수신
  S0 --> S1: 파일 파싱(Tool1)
  S1 --> S0: 실패재업로드
  S1 --> UI: 누락 존재
  S1 --> S2: 파싱 OK

  state S2 {
    direction TB
    [*] --> V1
    V1: 규정검증(Tool2.validate)
    V1 --> V2: Major 위반
    V2: normalize재검증
    V2 --> V1
    V1 --> V3: 커버리지 부족
    V3: 스니펫 확장
    V3 --> V1
    V1 --> Done: 통과
  }
  S2 --> S3: 규정 통과
  S3: 생성(Tool3.generate)
  S3 --> S2: YAML 실패
  S3 --> S4: 초안 + 인용
  S4: 결과 반환
  S4 --> [*]
  note right of S1: missing_required > 0 -> UI
  ```
---
## 2) 규칙+상태값 기반 Tool 라우터(가드 규칙+점수식)
  ```mermaid
flowchart TB
  subgraph Blackboard[블랙보드 상태]
    M1["parse.ok, missing_required, completeness, parse_conf"]
    M2["reg.validated, pass, violations, coverage, rag_conf"]
    M3["gen.yaml_lint_ok, citations_bound"]
  end

  A[Router] -->|가드| G1{필수 누락 있음?}
  G1 -- 예 --> UI1[[중단: 누락 안내]]
  G1 -- 아니오 --> G2{파싱 실패?}
  G2 -- 예 --> T1[Tool1]
  G2 -- 아니오 --> G3{규정 미검증?}
  G3 -- 예 --> T2[Tool2]
  G3 -- 아니오 --> G4{준수 통과 AND 완결성 95% 이상?}
  G4 -- 예 --> T3[Tool3]
  G4 -- 아니오 --> T2

  ```

  ---
## 스코어링(라우팅 우선순위)
-score(T1)= 1 - [parse.ok]
-core(T2)= [parse.ok] * (1 - [reg.validated])
-core(T3)= [parse.ok] * [reg.pass] * [completeness≥0.95]
-선택=argmax(score)  + 가드규칙(강제 라우팅)

---
## 3)블랙보드 I/O(도구 간 공유 상태)
```mermaid
flowchart LR
  %% 레이아웃
  subgraph T[Tools]
    direction TB
    T1["Tool1SmartDocumentTool"]
    T2["Tool2RegulationTool"]
    T3["Tool3GenerationTool"]
  end
  subgraph BB[Blackboard]
    direction TB
    P[("parse.summary")]
    R[("reg.status")]
    G[("gen.status")]
    C[("citations")]
  end
  Router[Agent Router]

  %% write(실선), read(점선) - 라벨 제거로 겹침 방지
  Router --> P
  Router --> R
  Router --> G
  Router --> C

  T1 --> P
  T2 --> R
  T3 --> G
  T3 --> C

  T1 -.-> P
  T2 -.-> P
  T3 -.-> P
  T3 -.-> R
  T2 -.-> C

  %% 범례
  subgraph Legend[Legend]
    W1[write] --> W2[ ]
    R1[read] -.-> R2[ ]
  end
```
---
## 4)ReAct 시퀀스(Thought->Action->Observation 루프)
```mermaid
sequenceDiagram
  participant U as 사용자
  participant A as Agent(Thought)
  participant T1 as Tool1
  participant T2 as Tool2
  participant T3 as Tool3
  participant V as YAML 검증
  participant X as XAI

  U->>A: 파일 업로드
  loop max_iters 이하
    A->>T1: Action parse()
    T1-->>A: Observation fields, missing_required
    alt 누락 존재
      A-->>U: UI 누락 알림(필드/예시)
    else 누락 없음
      A->>T2: Action validate()
      T2-->>A: Observation pass/violations/coverage
      alt Major 위반
        A->>T2: Action normalize()
        T2-->>A: Observation fixed?
      else 커버리지 부족
        A->>T2: Action search_more()
        T2-->>A: Observation 추가 스니펫
      end
      A->>T3: Action generate()
      T3-->>A: Observation draft, yaml_lint_ok?
      alt YAML 실패
        A->>V: 보정 원인 수집
        A->>T2: 재검증 또는 데이터 보정
      else 통과
        A->>X: 근거 트레이싱
        X-->>U: 본문 + 인용
      end
    end
  end

```
---
## 5) 모델 내부 아키텍처(추론 경로)
```mermaid
flowchart LR
  U["사용자 요청"] --> N["요청 정규화,파싱<br/>(언어/CTD 섹션 인식)"]

  subgraph RAG [RAG 검색 계층]
    Qe["임베딩(Qwen3 0.6B)"] --> Ret["Qdrant 검색<br/>(벡터+메타필터)"]
    BM25["BM25 키워드"] --> Ret
    Ret --> MMR["MMR 다양성"] --> TopK["상위 k 스니펫"]
  end

  N --> Qe
  N --> BM25
  N --> Ret

  subgraph PB [프롬프트 빌더]
    Tmpl["CTD 템플릿 슬롯<br/>+ 체크리스트(YAML)"] --> Ctx["컨텍스트 윈도 관리"]
    Ctx --> Cite["인용 주입<br/>(문서ID,섹션,페이지)"]
  end
  TopK --> Tmpl
  Cite --> G

  G["Llama 3.2 1B/3B<br/>llama.cpp,양자화"] --> Draft["초안"]

  subgraph POST [사후 처리,검증]
    Draft --> SOut["구조화 파서(JSON)"]
    SOut --> Valid["체크리스트 검증(YAML)"]
    SOut --> Trace["XAI 문장-근거 매핑"]
    Valid --> Fix["자가수정 루프"] --> G
  end

  Trace --> OUT["최종 결과<br/>본문+인용+NEED_INPUT"]
  Valid --> OUT
```
---

## 6) 데이터 인덱싱 파이프라인
```mermaid
flowchart TB
  A["원문 수집<br/>ICH,MFDS,WHO,기관 서식"] --> B["Upstage Document Parse"]
  B --> C["CTD 섹션 자동 매핑<br/>(M1~M3)"]
  C --> D["청크,표/그림 캡션 분리"]
  D --> E["메타 태깅<br/>{출처,연도,버전,섹션,페이지,문단ID}"]
  E --> F["임베딩(Qwen3 0.6B)"]
  F --> G[(Qdrant 컬렉션)]
  E --> H["BM25 인덱스"]
```
---
## 7) UI 피드백 플로우(누락/위반 리포트)

```mermaid
flowchart TB
  Start[분석 결과 수신] --> C1{필수 누락 있음?}
  C1 -- 예 --> U1[[UI: 필수 정보 누락- Lactose 기능- Starch 기능 조치: Excel 기능 필드 채우고 재업로드]]
  C1 -- 아니오 --> C2{Major 위반 있음?}
  C2 -- 예 --> U2[[UI: 규정 위반 리포트 조항, 현재값, 허용값, 자동수정 diff]]
  C2 -- 아니오 --> Done[[최종 결과 전달]]

```
---

## 8) 도구 I/O 스키마(요약)
```mermaid
classDiagram
  class Tool1_out {
    map fields
    string[] missing_required
    string[] missing_optional
    float completeness
    float parse_conf
    map ctd_slot_map
  }
  class Tool2_out {
    bool validated
    bool pass
    Violation[] violations
    float coverage
    float rag_conf
    map normalized_fields
    Citation[] citations
  }
  class Tool3_out {
    string draft_doc
    bool yaml_lint_ok
    Lint finding[]
    Trace[] trace_links
  }
  class Violation {string id; string section; string severity; string rule}
  class Citation {string doc; string section; int page; string para_id}
  class Lint {string key; string reason; string fix_hint}
  class Trace {string sentence_id; string citation_id}
```
---
## 용어
-CTD(Common Technical Document, 의약품 공통기술문서)

-ICH(International Council for Harmonisation, 국제 의약품 규제 조화)

-MFDS(식품의약품안전처, 한국 규제기관)

-YAML(규칙,체크리스트 기술 포맷)

-Qdrant(벡터DB)

-Upstage Document Parse(문서 파싱)

-Llama 3.2 1B/3B(온디바이스 추론/생성)
