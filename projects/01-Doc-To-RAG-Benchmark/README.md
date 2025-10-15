# PyPI Upload Demo

패키지화된 FastAPI 서버와 Vite + React + TypeScript + Tailwind CSS 프론트엔드를 하나로 묶은 파일 업로드 데모입니다. 사용자는 브라우저에서 여러 파일을 업로드할 수 있으며, 업로드된 파일의 이름·확장자·크기·업로드 시간을 테이블로 확인할 수 있습니다. 빌드된 정적 리소스는 Python 패키지 안에 포함되어 PyPI 배포를 통해 전달됩니다.

## 주요 구성 요소

- **FastAPI**: 업로드 처리, 정적 자산 제공, 업로드 메타데이터 저장(JSON 파일)
- **Vite + React 19 + TypeScript**: 업로드 UI와 테이블 표시
- **Tailwind CSS**: 반응형 UI 스타일링
- **Uvicorn**: ASGI 서버 실행기 (콘솔 스크립트 `pypi-test-app` 제공)

## 프로젝트 구조

```
.
├── frontend/                     # Vite + React + Tailwind 원본 코드
├── scripts/
│   └── build_frontend.py         # 프론트엔드 빌드 + 정적 자산 복사 스크립트
├── src/
│   └── pypi_test_app/
│       ├── api/                  # FastAPI 라우터 및 의존성
│       ├── static/               # 빌드된 프론트엔드 (PyPI 패키지에 포함)
│       ├── cli.py                # uvicorn 실행 진입점
│       ├── main.py               # FastAPI 앱 팩토리 및 정적 파일 설정
│       ├── storage.py            # 파일 저장 및 메타데이터 관리자
│       ├── schemas.py            # Pydantic 스키마
│       └── __init__.py
├── setup.py                      # 패키징 스크립트 (프론트 빌드 포함)
├── pyproject.toml                # PEP 517 빌드 설정
├── MANIFEST.in                   # 정적 자산 포함 규칙
└── README.md
```

## 개발 환경 준비

사전 요구 사항:

- Node.js 20 이상
- npm 10 이상
- Python 3.10 이상

### 1. 프론트엔드 개발 서버

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:5173` 로 접속하면 프론트엔드만 실행됩니다. 파일 업로드 API는 `http://localhost:8000/api/uploads` 로 프록시되므로, 백엔드 서버도 함께 실행해야 정상 동작합니다.

### 2. 백엔드 실행 (개발 모드)

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e .
# 또는 개발에 필요한 라이브러리를 수동 설치: fastapi uvicorn python-multipart

# hot reload 포함 실행 (프론트엔드 dev 서버와 연동)
pypi-test-app --reload --host 127.0.0.1 --port 8000
```

업로드된 파일과 메타데이터는 기본적으로 `~/.pypi_test_app/uploads` 경로에 저장되며, `PYPI_TEST_APP_STORAGE` 환경 변수를 통해 변경할 수 있습니다.

## 빌드 및 배포 절차

1. **프론트엔드 빌드**: `scripts/build_frontend.py`가 자동으로 `npm install` → `npm run build` → `src/pypi_test_app/static` 복사를 수행합니다. 이 스크립트는 `python scripts/build_frontend.py`로 수동 실행하거나, `python -m build`/`pip wheel .` 등 패키지 빌드 시 `setup.py`의 커스텀 `build_py` 명령에서 자동 실행됩니다.
2. **패키지 생성**:
   ```bash
   python -m build  # wheel, sdist 생성
   ```
3. **(옵션) PyPI 업로드**:
   ```bash
   python -m twine upload dist/*
   ```

자동 빌드를 건너뛰고 싶다면 `SKIP_FRONTEND_BUILD=1` 환경 변수를 설정한 후 `python -m build`를 실행합니다.

## API 개요

| Method | Endpoint        | 설명                              |
|--------|-----------------|-----------------------------------|
| GET    | `/api/uploads`  | 업로드된 파일 메타데이터 리스트 반환 |
| POST   | `/api/uploads`  | 다중 파일 업로드 (필드명: `files`) |

응답 예시:

```json
[
  {
    "id": "f3e3c8ec-4b0c-4a8b-96df-2ef2c4efbafe",
    "original_name": "example.pdf",
    "stored_name": "20250301094512_2d0983765c8c4bcbaa0fb640130beef3.pdf",
    "size_bytes": 102400,
    "extension": "pdf",
    "uploaded_at": "2025-03-01T09:45:12.124503+00:00"
  }
]
```

## 테스트

- **프론트엔드**: `npm run build` 로 타입 체크 & 프로덕션 번들 검증.
- **백엔드**: FastAPI/pytest 기반 테스트는 포함되어 있지 않지만, `uvicorn`으로 서버를 띄운 뒤 수동으로 업로드 API를 확인할 수 있습니다.

## 라이선스

프로젝트 루트에 라이선스를 추가해 배포 정책을 명시하세요 (예: MIT License). 현재 `setup.py` 메타데이터는 MIT License를 가리키고 있습니다.
