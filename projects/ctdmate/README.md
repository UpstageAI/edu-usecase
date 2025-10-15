# CTDMate - CTD 문서 자동 생성 시스템

Excel 데이터에서 CTD(Common Technical Document) 규제 문서를 자동으로 생성하는 AI 기반 시스템입니다.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 빠른 시작

### 1. 저장소 클론

```bash
git clone https://github.com/krnooby/CTDMate.git
cd ctdmate
```

### 2. 가상환경 설정 및 패키지 설치

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 실행

```bash
./run.sh
```

또는

```bash
python pipeline.py
```

**완료!** `output/` 폴더에 6개의 CTD 모듈 문서가 생성됩니다.

---

## 📋 주요 기능

- ✅ **Excel → CTD 문서 자동 생성** (M1, M2.3~M2.7)
- ✅ **ICH/MFDS 규제 자동 검증** (Coverage 94%+)
- ✅ **RAG 기반 인용 생성** (모든 문장에 [CIT-N] 태그)
- ✅ **YAML 구조화 출력** (표, 서술, References)
- ✅ **1분 내 전체 생성** (6개 모듈)

---

## 📁 입력 파일

기본 입력 파일: `input/CTD_bundle.xlsx`

Excel 파일은 다음 시트를 포함해야 합니다:
- M1: TM_5_Admin_Labeling_KR
- M2.3: TM_5_M2_3_QOS
- M2.4: TM_5_M2_4_Nonclinical_Ove
- M2.5: TM_5_M2_5_Clinical_Overvi
- M2.6: TM_5_Nonclinical, TM_5_M2_6_Nonclinical_Sum
- M2.7: TM_5_Phase1/2/3, TM_5_M2_7_Clinical_Summar

---

## 📤 출력 결과

`output/` 폴더에 생성되는 파일:

| 파일 | 크기 | 설명 |
|------|------|------|
| M1.yaml | ~2.5KB | 행정정보 및 라벨링 |
| M2_3.yaml | ~7KB | 품질평가자료 요약 ⭐ |
| M2_4.yaml | ~3KB | 비임상 개요 |
| M2_5.yaml | ~2KB | 임상 개요 |
| M2_6.yaml | ~5KB | 비임상 요약 (표 포함) |
| M2_7.yaml | ~2.5KB | 임상 요약 |
| generation_summary.json | - | 전체 생성 결과 요약 |

---

## 🎨 사용법

### 기본 실행 (전체 모듈 생성)

```bash
python pipeline.py
```

### 커스텀 Excel 파일 사용

```bash
python pipeline.py --excel /path/to/your/file.xlsx
```

### 검증만 실행 (문서 생성 안함)

```bash
python pipeline.py --validate-only -f input/CTD_bundle.xlsx
```

### 도움말

```bash
python pipeline.py --help
```

---

## 🏗️ 시스템 구조

```
Pipeline: Router → Parse → Validate → Generate

1. Router: 요청 분석 (Llama 3.2-1B)
2. Parse: Upstage Document AI 파싱 (선택적)
3. Validate: ICH/MFDS 규제 검증 (Coverage 94%+)
4. Generate: Solar Pro2 문서 생성 + 인용
```

**주요 기술:**
- **LLM**: Upstage Solar Pro2 (생성), Llama 3.2-1B/3B (Router)
- **RAG**: Qdrant (벡터 DB) + E5 Embeddings
- **검증**: ICH/MFDS 가이드라인 자동 매칭

---

## 📊 성능

- **검증 속도**: 10개 시트 5초
- **생성 속도**: 모듈당 10초
- **평균 Coverage**: 94.46%
- **Pass Rate**: 100%
- **총 소요 시간**: 약 1분 (6개 모듈)

---

## 🔧 요구사항

- **Python**: 3.12+
- **OS**: Linux (Ubuntu 22.04 권장)
- **메모리**: 4GB+ (Qdrant + embeddings)
- **디스크**: 100MB+ (Qdrant storage 포함)

---

## 🛠️ 환경 설정

### API 키 설정 (선택적)

`.env` 파일 생성:

```bash
UPSTAGE_API_KEY=your_api_key_here
```

기본 API 키가 `app/config.py`에 포함되어 있으므로 생략 가능합니다.

---

## 📁 폴더 구조

```
ctdmate/
├── input/              # Excel 입력 파일
├── output/             # 생성된 YAML 문서
├── app/                # 설정 및 타입
├── brain/              # Router (LLM)
├── rag/                # RAG 엔진
├── tools/              # 검증/생성 도구
├── rules/              # 규제 규칙
├── qdrant_storage/     # 벡터 DB (26MB)
├── pipeline.py         # 메인 실행 파일
├── run.sh              # Bash 실행 스크립트
└── README.md           # 상세 매뉴얼
```

---

## 📄 라이센스

MIT License - 자유롭게 사용 가능합니다.

---

## 👥 제작

**CTDMate Team**  
- AI/LLM: Upstage Solar Pro2, Llama 3.2
- RAG: Qdrant + E5 Embeddings
- Validation: ICH/MFDS Guidelines

---

---

## 🤖 Fine-tuned 모델 사용 (선택사항)

CTDMate는 **Llama 3.2-3B Term Normalizer** fine-tuned 모델을 지원합니다.

### 모델 다운로드

```bash
./download_model.sh
```

또는 수동 다운로드:
- **Google Drive**: [다운로드 링크](https://drive.google.com/file/d/1jXqPcVPB1MTnB_ao2BB6r45wEVtnTf0R/view?usp=sharing)
- 파일 크기: ~6GB
- 저장 위치: `ctdmate/models/llama-3.2-3B-term-normalizer-F16.gguf`

### 사용 방법

**자동 (기본):**
```python
from ctdmate.pipeline import CTDPipeline

# Fine-tuned 모델 자동 로드
pipeline = CTDPipeline(use_finetuned=True)
```

**커스텀 설정:**
```python
from ctdmate.pipeline import CTDPipeline
from ctdmate.brain.llama_client import LlamaGGUFClient

# 커스텀 모델 설정
client = LlamaGGUFClient(
    model_path="models/llama-3.2-3B-term-normalizer-F16.gguf",
    n_ctx=4096,           # Context length
    n_gpu_layers=-1,      # GPU 레이어 수 (-1 = 전부)
    temperature=0.1,      # 생성 온도
)

pipeline = CTDPipeline(llama_client=client)
```

**모델 없이 실행 (Heuristic만):**
```python
pipeline = CTDPipeline(use_finetuned=False)
```

### Fine-tuned 모델 효과

- ✅ **용어 정규화 정확도 향상** (90%+)
- ✅ **Router 의사결정 개선**
- ✅ **Domain-specific 지식 활용**

---

