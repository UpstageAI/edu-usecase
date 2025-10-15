"""
설정 파일
모든 시스템 설정을 중앙 관리
"""

import os
from pathlib import Path
from typing import Optional, Union

from dotenv import load_dotenv

# 타입 별칭
PathType = Union[str, os.PathLike]

# .env 파일 로드
load_dotenv()


def _resolve_project_root(candidate: Optional[PathType] = None) -> Path:
    """OCR 에이전트 자산을 저장할 루트 경로를 계산."""

    if candidate:
        return Path(candidate).expanduser().resolve()

    env_override = os.getenv("OCR_AGENT_BASE_DIR")
    if env_override:
        return Path(env_override).expanduser().resolve()

    return Path(__file__).parent.resolve()


def _apply_project_root(base_dir: Path) -> None:
    """주어진 *base_dir*를 기준으로 경로 상수를 갱신."""

    global PROJECT_ROOT, DATA_DIR, INPUT_DIR, OUTPUT_DIR, TEMP_DIR
    global REPORTS_DIR, TABLES_DIR, EXTRACTED_DIR, VALIDATED_DIR, JUDGED_DIR
    global LOG_FILE

    PROJECT_ROOT = base_dir
    DATA_DIR = PROJECT_ROOT / "data"
    INPUT_DIR = DATA_DIR / "input"
    OUTPUT_DIR = DATA_DIR / "output"
    TEMP_DIR = DATA_DIR / "temp"

    REPORTS_DIR = OUTPUT_DIR / "reports"
    TABLES_DIR = OUTPUT_DIR / "tables"

    EXTRACTED_DIR = TEMP_DIR / "extracted"
    VALIDATED_DIR = TEMP_DIR / "validated"
    JUDGED_DIR = TEMP_DIR / "judged"

    LOG_FILE = PROJECT_ROOT / "agent_system.log"


# 초기 경로 설정
_apply_project_root(_resolve_project_root())

# LLM API 설정 - Upstage Solar pro2
SOLAR_API_KEY: Optional[str] = os.getenv("SOLAR_API_KEY")
if not SOLAR_API_KEY:
    print("[경고] SOLAR_API_KEY가 설정되지 않았습니다. 요청 헤더 또는 환경 변수로 전달하세요.")

SOLAR_API_BASE = "https://api.upstage.ai/v1"
SOLAR_MODEL = "solar-pro2"
SOLAR_MAX_TOKENS = 4096
SOLAR_TEMPERATURE = 0.3

# Upstage API 비용 (per page)
UPSTAGE_API_PRICING = {
    "upstage_ocr": 0.0015,           # $0.0015 per page
    "upstage_document_parse": 0.01,  # $0.01 per page
    "pdfplumber": 0.0,               # 오픈소스 (무료)
    "pdfminer": 0.0,                 # 오픈소스 (무료)
    "pypdfium2": 0.0                 # 오픈소스 (무료)
}

# OCR/파싱 도구 설정
# pdfplumber
PDF_PLUMBER_LAYOUT_WIDTH_TOLERANCE = 3
PDF_PLUMBER_LAYOUT_HEIGHT_TOLERANCE = 3

# Custom Split (LR-Split) 설정
CUSTOM_SPLIT_AXIS = "vertical"  # vertical: 좌/우 분할
CUSTOM_SPLIT_OVERLAP_PX = 10
CUSTOM_SPLIT_MARGIN_LEFT = 50
CUSTOM_SPLIT_MARGIN_RIGHT = 50
CUSTOM_SPLIT_DPI = 300
CUSTOM_SPLIT_MIDLINE_DETECTION = "auto"  # auto or fixed

# 유효성 검증 임계치 (1.0=Pass, 0.0=Fail 방식)
VALIDATION_THRESHOLDS = {
    "read": 0.5,   # 읽기 순서 (Pass/Fail)
    "sent": 0.5,   # 문장 완결성 (Pass/Fail)
    "noise": 0.5,  # 노이즈 제거 (Pass/Fail)
    "table": 0.5   # 표 파싱 (Pass/Fail)
}

# 폴백 설정
MAX_FALLBACK_ATTEMPTS = 2  # 각 축별 최대 재시도 횟수
MIN_IMPROVEMENT_DELTA = 0.1  # 최소 개선폭 (Pass/Fail 방식: 0.1 이상)
FALLBACK_PRIORITY = [
    "custom_split",      # 1. 좌우 분할 (PDF 전처리 후 재추출)
    "layout_reorder",    # 2. 레이아웃 재정렬
    "table_enhancement"  # 3. 표 강화
]

# LLM Judge 평가 가중치 (각 점수 0-100)
JUDGE_WEIGHTS = {
    "S_read": 0.25,      # 25% - 읽기 순서
    "S_sent": 0.25,      # 25% - 문장 완결성
    "S_noise": 0.15,     # 15% - 노이즈 제거
    "S_table": 0.25,     # 25% - 표 파싱
    "S_fig": 0.10        # 10% - 그림/도표
}

# 점수 기준 (0-100 범위)
SCORE_THRESHOLDS = {
    "pass": 85,          # 85점 이상: 우수
    "borderline": 70,    # 70-85점: 양호
    # 70점 미만: 개선 필요 (하지만 2단계 Pass 받았으므로 실무 사용 가능)
}

# 최종 선택 가중치
SELECTION_WEIGHTS = {
    "score": 0.8,        # 품질 점수
    "speed": 0.2         # 처리 속도
}

# 로깅 설정
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 멀티프로세싱 설정
MAX_WORKERS = 4  # 병렬 처리 워커 수
BATCH_SIZE = 10  # 배치 처리 크기

# 타임아웃 설정 (초)
OCR_TIMEOUT = 300         # OCR 처리 타임아웃
VALIDATION_TIMEOUT = 60   # 검증 타임아웃
LLM_TIMEOUT = 120         # LLM 호출 타임아웃

# 디버그 모드
DEBUG_MODE = False
SAVE_INTERMEDIATE_FILES = True  # 중간 파일 저장 여부

# 지원 파일 형식
SUPPORTED_FORMATS = [".pdf", ".hwp"]

# 출력 파일명
OUTPUT_FILES = {
    "full_combinations": "full_combinations.csv",
    "final_selection": "final_selection.csv",
    "failed_documents": "failed_documents.csv",
    "judge_report": "judge_report.json"
}


def create_directories() -> None:
    """필요한 모든 디렉토리 생성"""

    directories = [
        INPUT_DIR,
        OUTPUT_DIR,
        TEMP_DIR,
        REPORTS_DIR,
        TABLES_DIR,
        EXTRACTED_DIR,
        VALIDATED_DIR,
        JUDGED_DIR,
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    print(f"[OK] 디렉토리 구조 생성 완료: {PROJECT_ROOT}")


def set_project_root(
    base_dir: Optional[PathType] = None,
    *,
    ensure_directories: bool = True,
) -> Path:
    """OCR 에이전트가 사용할 루트 경로를 재설정."""

    new_root = _resolve_project_root(base_dir)
    _apply_project_root(new_root)

    if ensure_directories:
        create_directories()

    return PROJECT_ROOT


def set_api_key(value: Optional[str]) -> None:
    """외부에서 전달된 API 키를 설정."""

    global SOLAR_API_KEY
    SOLAR_API_KEY = value
    if value:
        os.environ["SOLAR_API_KEY"] = value
    else:
        os.environ.pop("SOLAR_API_KEY", None)


def get_api_key() -> Optional[str]:
    """현재 설정된 API 키 반환."""

    return SOLAR_API_KEY


if __name__ == "__main__":
    create_directories()
