# CTDMate
규칙+RAG 기반 CTD 인허가 문서 작성,검증 에이전트 
데이터입력 → Upstage Document Parse → CTD 자동 매핑 → 인용형 검색(ICH,MFDS) → YAML 체크 → 근거 하이라이트
LLM 사용은 선택(초안,요약,용어 통일) 온디바이스(llama.cpp, LoRA, 양자화) 지원

---

## 요구사항
- Python 3.12.11
- OS: Ubuntu Linux 22.04

## 설치
```bash
git clone https://github.com/krnooby/CTDMate.git
cd CTDMATE
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env .env.example
# CTDMate
