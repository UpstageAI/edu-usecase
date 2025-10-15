
# 프로젝트 명: 특허·지식재산권 정보와 기술 동향을 제공하는 AI 챗봇

<br><br>

## 팀원 소개

- 팀장: 양문규
- 팀원: 김영은
- 팀원: 손단하
- 팀원: 최서영
- 팀원: 성수린

<br>

## 프로젝트 개요

- 지식재산권/특허 특화 LLM 챗봇 에이전트를 통해 빅데이터•인공지능/컴퓨팅•소프트웨어 분야 창업가에게 특허·지식재산권 정보와 기술 동향을 제공하는 AI 기반 대화형 플랫폼

<br>

## 주요 기능

- 스타트업 창업 맞춤형 지식재산권/특허 관련 정보 제공
- RAG Pipeline을 통한 신뢰성 있는 답변 제공
- Fine-tuning On-device LLM을 통한 사용자 정보 보안 강화

<br>

## 기술 스택 및 아키텍처

### 기술 스택

- AI: Langchain, Langgraph
- UI: Streamlit
- Fine-tuning: llama.cpp, Docker

### 아키텍처

![image.png](아키텍쳐)

<br><br>

# Patent-LLAMA (RAG + 라우터)

로컬 라우터(3B, GGUF, `llama-server`)와 외부 LLM(Upstage Solar)을 결합한 특허/법률 RAG 데모입니다.  
Streamlit 앱에서 질의 → 라우팅(로컬) → 검색/요약/리트리브 → 답변(외부 LLM) 순서로 동작합니다.

```bash
[User] → Streamlit(8501)
├─ Router (local GGUF via llama-server:8000)
│     └─ tool = retrieve / web / answer
├─ Web search (Tavily POST /search) → fetch(HTML→텍스트) → summarize
├─ Retrieval (Embedding API → Qdrant multi-collections)
└─ Final Answer (Upstage Solar /v1/solar/chat/completions)
```

<br><br>

## 0) 사전 준비 (파인튜닝 모델)

본 프로젝트는 로컬 라우터 모델(`router-q8.gguf`)을 기반으로 동작합니다.  
이 모델은 **Llama-3.2-3B-Instruct**를 QLoRA 방식으로 파인튜닝한 결과물을 GGUF로 변환한 것입니다.  

* 파인튜닝 데이터: 특허·법률 QA (instruction / input / output 포맷)
* 학습 방식: SFT + QLoRA (LoRA r=8~16, seq_len=1024)
* 변환 방식: llama.cpp → `router-q8.gguf`

따라서 실행 전에 다음 파일이 준비되어야 합니다:

```bash
C:\patent-llama\llama.cpp\router-q8.gguf
```

> 이 파일이 없으면 라우터 노드(`node_route.py`)가 동작하지 않습니다.

<br><br>

## 1) 필수 요건

* Docker Desktop (Windows)
* (선택) NVIDIA GPU + Docker GPU 지원
* 위에서 설명한 `router-q8.gguf`가 반드시 존재해야 함

<br>

## 2) 디렉터리 구조(요약)

```bash
C:\patent-llama
├─ docker
│   ├─ Dockerfile.infer        # llama-server 실행용
│   └─ Dockerfile.streamlit    # 앱
├─ src
│   ├─ app\ui_demo.py          # Streamlit 엔트리
│   ├─ core*.py               # LLM/Embed/Qdrant 클라이언트
│   └─ graph...               # 노드/흐름(라우팅, 웹검색, 리트리브, 답변)
├─ llama.cpp\router-q8.gguf    # 로컬 라우터 모델(GGUF)
├─ docker-compose.yml
└─ .env
````

<br><br>

## 3) 환경변수(.env) 템플릿

> **반드시** 프로젝트 루트 `C:\patent-llama\.env`에 저장하세요.


```env
# ── 라우터(로컬 GGUF / llama-server)
GGUF_MODEL=C:\patent-llama\llama.cpp\router-q8.gguf
INFER_PORT=8000
CTX=4096

# ── 외부 LLM (Upstage Solar)
MODEL_PROVIDER=upstage
UPSTAGE_API_KEY=sk-...                 
UPSTAGE_BASE_URL=https://api.upstage.ai/v1/solar
UPSTAGE_MODEL=solar-1-mini-chat        

# ── 웹검색 (Tavily)
SEARCH_API=tavily
TAVILY_API_KEY=tvly-...                
TAVILY_URL=https://api.tavily.com/search
WEB_RESULTS=5
WEB_FETCH_TOP=3

# ── 컨텍스트 예산
WEB_PAGE_CHAR_BUDGET=4000
WEB_CTX_CHAR_BUDGET=12000
CTX_BUDGET_CHARS=15000

# ── Qdrant
QDRANT_URL=http://your-qdrant:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=patent_db

# ── 임베딩 API
EMBED_URL=https://your-embed.example.com/embed
EMBED_API_KEY=...
EMBED_MAX_BATCH=32

# ── 내부 경로/파이썬
PYTHONPATH=/workspace/src
````

<br><br>

## 4) 실행/중지(가장 간단)

```powershell
docker compose up -d         
docker compose ps            
start http://localhost:8501  
```

<br>

개별 실행:

```powershell
docker compose up -d inference   # 로컬 라우터 서버만(8000)
docker compose up -d app         # 앱만(8501)
```

중지:

```powershell
docker compose down
```

<br><br>

## 5) 헬스체크

라우터 서버:

```powershell
curl.exe http://127.0.0.1:8000
```

앱 접속:

```
http://localhost:8501
```

<br><br>

## 6) 코드 변경 반영

* Streamlit 코드만 변경 → `docker compose restart app`
* requirements 변경 → `docker compose build app && docker compose up -d app`
* inference 변경 → `docker compose build inference && docker compose up -d inference`

<br><br>

## 7) 로그 보기

```powershell
docker logs -f patent-llama-inference-1
docker logs -f patent-llama-app-1
```

<br><br>

## 8) 자주 발생하는 이슈 & 해결

* **앱 접속 에러**: `http://localhost:8501`로 접속
* **Tavily 405**: 반드시 `POST /search` 사용
* **Upstage 400(context_length_exceeded)**: `WEB_*_BUDGET`, `CTX_BUDGET_CHARS` 조정
* **Windows 경로 매핑**: `.env`의 `GGUF_MODEL` 경로 확인

<br><br>

## 9) 내부 동작(요약)

* `flow.py`: 전체 orchestration
* `route.py`: 로컬 GGUF 라우터 호출 → tool 결정
* `web_query.py`: Tavily 검색
* `web_fetch.py`: HTML → 텍스트 변환
* `retrieve.py`: 임베딩 API → Qdrant 검색
* `answer.py`: Upstage Solar 호출

<br><br>

## 10) 개발 팁

* `.env` 수정 후 → 최소 `docker compose restart app` 필요
* 앱의 Router/Debug 패널로 문제 원인 추적 가능

<br><br>

