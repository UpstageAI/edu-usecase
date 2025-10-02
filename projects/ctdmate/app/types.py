# ctdmate/app/types.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypedDict, Literal

try:
    from typing import NotRequired
except ImportError:
    from typing_extensions import NotRequired

# -------------------------
# Lint: YAML 정합성 리포트 항목
# dataclass로 정의해 직접 생성 가능(Lint(key=..., reason=..., fix_hint=...)).
# dict로 직렬화가 필요하면 obj.__dict__ 사용.
# -------------------------
@dataclass(slots=True)
class Lint:
    key: str
    reason: str
    fix_hint: str

# -------------------------
# 공용 리터럴
# -------------------------
Action = Literal["generate", "validate", "parse", "pipeline"]
OutputFormat = Literal["yaml", "markdown"]
Severity = Literal["minor", "major", "critical"]

# -------------------------
# Router(plan) 결과
# -------------------------
class RoutePlan(TypedDict, total=False):
    action: Action
    section: str                     # 예: "M2.3", "M2.6", "M2.7"
    need_parse: bool
    need_rag: bool
    need_generate: bool
    need_validate: bool
    output_format: OutputFormat

# -------------------------
# RAG 검색/인용 메타
# -------------------------
class GuidelineMeta(TypedDict, total=False):
    source: str                      # 문서 경로/식별자
    module: str                      # CTD 모듈(예: M2.6)
    page: int | str | None
    para_id: NotRequired[str]

class GuidelineResult(TypedDict, total=False):
    content: str
    metadata: GuidelineMeta
    score: NotRequired[float]

class Citation(TypedDict, total=False):
    source: str
    section: str
    page: int | str | None
    snippet: str
    score: NotRequired[float]

# -------------------------
# 규제 위반 리포트 항목
# -------------------------
class Violation(TypedDict, total=False):
    type: str
    description: str
    suggestion: str
    severity: NotRequired[Severity]
    field: NotRequired[str]

# -------------------------
# Tool1: smartdoc_upstage.run() 결과
# -------------------------
class ParseItem(TypedDict):
    input: str
    markdown: str
    rag_jsonl: str
    pages: int

class ParseError(TypedDict):
    input: str
    error: str

class ParseOutput(TypedDict):
    ok: bool
    results: List[ParseItem]
    errors: List[ParseError]

# -------------------------
# Tool2: 규제 검증 결과
#  - 단일 섹션 validate_and_normalize()
# -------------------------
ValidateResult = TypedDict(  # 'pass' 키 유지를 위해 dict-스타일 선언
    "ValidateResult",
    {
        "validated": bool,
        "pass": bool,
        "violations": List[Violation],
        "normalized_content": str,
        "coverage": float,
        "citations": List[Citation],
        "rag_conf": float,
    },
    total=False,
)

# 시트 단위(엑셀) 결과 확장
class SheetResult(ValidateResult, total=False):
    sheet_name: str
    module: str

class ValidateExcelSummary(TypedDict):
    total_violations: int
    avg_coverage: float
    pass_rate: float

class ValidateExcelOutput(TypedDict):
    total_sheets: int
    validated_sheets: int
    results: List[SheetResult]
    summary: ValidateExcelSummary

# -------------------------
# Tool3: 생성기 결과(SolarGenerator.generate)
# -------------------------
class GenerateOutput(TypedDict, total=False):
    section: str
    format: OutputFormat
    text: str
    rag_used: bool
    rag_refs: List[Citation]
    lint_ok: bool
    lint_findings: List[Lint | Dict[str, Any]]
    offline_fallback: Optional[str]
    created_at: str

JsonDict = Dict[str, Any]

__all__ = [
    "Lint",
    "Action", "OutputFormat", "Severity",
    "RoutePlan",
    "GuidelineMeta", "GuidelineResult", "Citation",
    "Violation",
    "ParseItem", "ParseError", "ParseOutput",
    "ValidateResult", "SheetResult", "ValidateExcelSummary", "ValidateExcelOutput",
    "GenerateOutput",
    "JsonDict",
]
