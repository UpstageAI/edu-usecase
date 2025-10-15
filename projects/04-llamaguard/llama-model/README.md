### Llama Model Tuning

이 문서는 `meta-llama/Llama-3.2-1B-Instruct` 모델을 기반으로 코드 취약점 분석을 위한 QLoRA 파인튜닝 및 추론 방법을 안내합니다.

### 환경세팅

**1. 사전 요구사항**
- Python 3.9 이상
- Git
- NVIDIA GPU (CUDA 11.8 이상 권장, QLoRA 및 `bitsandbytes` 사용을 위해 필수)

**2. 프로젝트 클론**
```bash
git clone https://[your-repository-url]/llama-guard.git
cd llama-guard/llama-model
```

**3. 가상 환경 생성 및 활성화**
Python 가상 환경을 생성하고 활성화합니다. `uv` 또는 `venv`를 사용할 수 있습니다.

- **uv 사용 시 (권장, 빠름)**
  ```bash
  # uv 설치 (최초 1회)
  curl -LsSf https://astral.sh/uv/install.sh | sh
  
  # 가상환경 생성 및 활성화
  uv venv
  source .venv/bin/activate  # Linux/macOS
  .venv\Scripts\activate    # Windows
  ```

- **venv 사용 시**
  ```bash
  python -m venv .venv
  source .venv/bin/activate  # Linux/macOS
  .venv\Scripts\activate    # Windows
  ```

**4. 필수 패키지 설치**
`requirements.txt` 파일을 사용하여 필요한 라이브러리를 설치합니다.

- **uv 사용 시**
  ```bash
  uv pip sync requirements.txt
  ```
- **pip 사용 시**
  ```bash
  pip install -r requirements.txt
  ```
> **Note:** `torch`와 `bitsandbytes`는 CUDA 환경에 따라 설치 방법이 달라질 수 있습니다. 만약 GPU 관련 오류가 발생하면, 사용 중인 CUDA 버전에 맞는 PyTorch를 공식 홈페이지에서 확인하여 재설치하세요.

### 실행방법

**Step 1. 기본 모델 다운로드**
파인튜닝의 기반이 될 `meta-llama/Llama-3.2-1B-Instruct` 모델을 로컬에 다운로드합니다.

```bash
python llama_download.py
```
- 실행 시 `./llama-3.2-1B-Instruct` 디렉토리에 모델 파일이 저장됩니다.

**Step 2. 모델 파인튜닝 (QLoRA)**
준비된 데이터셋을 사용하여 기본 모델을 파인튜닝합니다. `llama_fine_tuning.py` 스크립트는 QLoRA 방식을 사용하여 적은 리소스로 모델을 튜닝합니다.

```bash
python llama_fine_tuning.py
```
- **입력:**
  - 기본 모델: `./llama-3.2-1B-Instruct`
  - 학습 데이터: `./data/Code_Vuln_DPO/secure_programming_dpo_flat.json`
- **출력:**
  - LoRA 어댑터: `./llama-3.2-1B-Instruct-vuln-lora/lora-adapter`
  - 병합된 전체 모델: `./merged-vuln-detector`
- 스크립트가 완료되면, 추론에 바로 사용할 수 있도록 LoRA 가중치가 기본 모델과 병합된 버전이 `./merged-vuln-detector`에 자동으로 저장됩니다.

**Step 3. 취약점 분석 추론 실행**
파인튜닝 및 병합이 완료된 모델을 사용하여 코드의 취약점을 분석합니다.

- **기본 예시 코드로 추론 실행:**
  ```bash
  python llama_predict.py --model "./merged-vuln-detector"
  ```

- **파일에 저장된 코드로 추론 실행:**
  ```bash
  python llama_predict.py --model "./merged-vuln-detector" --code_file "./test_func.py"
  ```

- **터미널에서 직접 코드를 입력하여 추론:**
  ```bash
  python llama_predict.py --model "./merged-vuln-detector" --code "def example(): return 'hello'"
  ```

### Model

- **Base Model**: `meta-llama/Llama-3.2-1B-Instruct`
- **Training Method**: QLoRA (Quantized Low-Rank Adaptation)
- **실행환경**: Window / Python (Linux에서도 동일하게 실행 가능)

### TODOLIST
- Input / Output 확인
  > Input : Code (함수 단위) / Output : Vuln_Description 
  > Vuln_Description : 취약점 설명 처럼 나오면 좋음.

- 데이터를 어떻게 학습시켜야하는지 
    (적합한 오픈 데이터 확인)
- 학습 및 추론 방법

### Dataset
[CyberNative/Code_Vulnerability_Security_DPO](https://huggingface.co/datasets/CyberNative/Code_Vulnerability_Security_DPO)

- 프로젝트 계획서
```
팀 정보
    팀명: 라마 가드 (LLaMA Guard)
    팀원 정보
    팀장: TBD 
팀원:  원인영, 현규원, 정석희, 백승윤, 우지수

프로젝트 정보
- 프로젝트 주제
  코드 리뷰를 통한 자동 코드 취약점 분석 시스템

- 프로젝트 세부 내용
  이미 알려진 취약점과 그 예제 코드를 LLM에게 in-context learning이나 fine-tuning등을 통해 미리 학습시킴
  리뷰할 코드가 발생되면 미리 준비된 LLM을 통해 취약점이 발생할 가능성을 분석
  분석 내용의 정확도를 feedback등을 통해  상승시큼

- AI 활용 기술
  fine-tuning내지는 in-context 러닝: AI에게 취약한 코드의 설명 및 예시를 pair로 학습시켜서 보안에 입각한 코드 리뷰에 특화된 결과물을 내도록 유도
  - LLM에게 이 코드가 왜 위험한지를 자연어로 설명시키고, 코드 대안을 제시하도록 학습시킴2
```

- 프로젝트 구성도 가안
```MERMAID
graph TD
    A[코드 입력] --> B[Code Analysis Agent]
    B --> C{위험도 > 0.7?}
    C -->|Yes| D[Vector Search Agent]
    C -->|No| E[Report Generation Agent]
    D --> E
    E --> F[최종 취약점 리포트]

    G[LLaMA-1B-Instruct] --> B
    H[FAISS Vector DB] --> D
    I[Upstage API] --> E
```
