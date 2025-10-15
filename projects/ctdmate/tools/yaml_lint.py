# ctdmate/tools/yaml_lint.py
from __future__ import annotations
import re
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional

import yaml

# Lint 타입 임포트: 절대 → 상대 → 최종 폴백(TypedDict)
try:
    from ctdmate.app.types import Lint  # 패키지로 실행 시
except Exception:
    try:
        from ..app.types import Lint  # 모듈 상대 임포트
    except Exception:
        from typing import TypedDict  # 폴백 타입(런타임용)
        class Lint(TypedDict):
            key: str
            reason: str
            fix_hint: str

_RULES_CACHE: Optional[dict] = None
_RULES_PATH = Path(__file__).resolve().parents[1] / "rules" / "checklist.yaml"

def _load_rules(path: Optional[str] = None) -> dict:
    """
    규칙 YAML 로드. 기본 경로: <repo>/ctdmate/rules/checklist.yaml
    """
    global _RULES_CACHE
    if _RULES_CACHE is None or path:
        p = Path(path) if path else _RULES_PATH
        with open(p, "r", encoding="utf-8") as f:
            _RULES_CACHE = yaml.safe_load(f) or {}
    return _RULES_CACHE or {}

def _normalize_section(s: str) -> str:
    s = (s or "").strip().upper()
    return s if s.startswith("M") else f"M{s}"

def _block_for_section(rules: dict, section: str) -> dict:
    sec = _normalize_section(section)
    if sec.startswith("M2.6"):
        return rules.get("m2_6", {})
    # 기본은 M2.3 QOS 블록
    return rules.get("m2_3_qos", {})

def _textify(x: Any) -> str:
    if isinstance(x, str):
        return x
    return yaml.safe_dump(x, allow_unicode=True)

def _hit_red_flags(text: str, phrases: List[str]) -> List[str]:
    low = text.lower()
    return [p for p in phrases or [] if p and p.lower() in low]

# --- CSV 존재 감지(딕트/리스트/셋/문자열 모두 허용) ---
_M26_CSV_RE = re.compile(r"(?i)^m26_\d+_.*\.csv$")

def _has_m26_csv(csv_present: Any) -> bool:
    if not csv_present:
        return False
    names: List[str] = []
    if isinstance(csv_present, dict):
        names = [str(k) for k, v in csv_present.items() if v]
    elif isinstance(csv_present, (list, tuple, set)):
        names = [str(x) for x in csv_present]
    elif isinstance(csv_present, str):
        names = [csv_present]
    else:
        return bool(csv_present)
    return any(_M26_CSV_RE.match(Path(n).name) for n in names)

def _mk_lint(key: str, reason: str, fix_hint: str) -> Lint:  # 런타임 호환 생성기
    try:
        # dataclass/NamedTuple 형태일 때
        return Lint(key=key, reason=reason, fix_hint=fix_hint)  # type: ignore[arg-type]
    except Exception:
        # TypedDict 형태일 때
        return {"key": key, "reason": reason, "fix_hint": fix_hint}  # type: ignore[return-value]

def lint_yaml(
    yaml_text: str,
    section: str = "2.3",
    csv_present: Optional[Any] = None,   # dict|list|set|str 모두 허용
    checklist_path: Optional[str] = None,
) -> Tuple[bool, List[Lint]]:
    """
    CTD 섹션별 YAML 내용 정적 점검.

    Args:
        yaml_text: 검사 대상 YAML 문자열
        section: "M2.3"/"2.3", "M2.6"/"2.6" 등 섹션 표기 허용
        csv_present: M2.6에서 표(Tabulated) 파일 존재 힌트. dict|list|set|str 형태 허용
        checklist_path: 규칙 YAML 경로 재지정 시

    Returns:
        (ok, findings)
        ok: 위반 없음이면 True
        findings: List[Lint]  [{key, reason, fix_hint}]
    """
    findings: List[Lint] = []
    rules = _load_rules(checklist_path)
    block = _block_for_section(rules, section)
    sec = _normalize_section(section)
    is_m26 = sec.startswith("M2.6")
    is_m23 = sec.startswith("M2.3")

    # 1) 구문 검사
    try:
        data = yaml.safe_load(yaml_text)
    except Exception as e:
        return False, [_mk_lint("__yaml__", f"parse_error: {e}", "fix yaml syntax")]
    if not isinstance(data, dict):
        return False, [_mk_lint("__yaml__", "top-level must be a mapping", "make top-level a mapping")]

    # 2) 전역 금칙어
    rf = rules.get("global_red_flags", {})
    hits = _hit_red_flags(_textify(data), rf.get("phrases", []))
    if hits:
        findings.append(_mk_lint("__text__", f"red_flags: {', '.join(hits)}", "remove placeholders/vague terms"))

    # 3) 필수 키
    required: List[str] = []
    severities: Dict[str, str] = {}
    if is_m23:
        required = block.get("required", [])
        severities = block.get("severities", {})
    elif is_m26:
        required = block.get("required_keys_base", [])
        severities = block.get("severities", {})
        pol = block.get("policy", {})
        has_csv = _has_m26_csv(csv_present)
        if has_csv and pol.get("require_tabulated_if_csv", True):
            required = list(dict.fromkeys(required + ["TabulatedSummaries"]))
        if not has_csv and pol.get("require_written_if_no_csv", True):
            required = list(dict.fromkeys(required + ["WrittenSummary"]))

    for k in required:
        if k not in data or data.get(k) in (None, "", []):
            sev = severities.get(k, "minor")
            findings.append(_mk_lint(k, f"missing_required({sev})", "supply value"))

    # 4) M2.3 상세 규칙
    if is_m23:
        fields = block.get("fields", {})
        # 4-1) ProductName 패턴
        pr = fields.get("ProductName", {})
        patt = pr.get("pattern")
        if patt and isinstance(data.get("ProductName"), str):
            if re.fullmatch(patt, data["ProductName"]) is None:
                findings.append(_mk_lint("ProductName", "pattern_mismatch", "follow ProductName pattern"))
        # 4-2) DosageForm 허용값 체크(value_sets 참조)
        df = fields.get("DosageForm", {})
        av_ref = df.get("allowed_values_ref")
        if av_ref and isinstance(data.get("DosageForm"), str):
            vs = rules.get("value_sets", {})
            key = av_ref.replace("value_sets.", "")
            allowed = set(vs.get(key, []))
            if allowed and data["DosageForm"] not in allowed:
                findings.append(_mk_lint("DosageForm", f"not_in_allowed_values: {data['DosageForm']}", f"use one of: {sorted(allowed)}"))
        # 4-3) References 스키마
        if "References" in data:
            if not isinstance(data["References"], list):
                findings.append(_mk_lint("References", "type_mismatch(list expected)", "list of {doc,section,page,para_id}"))
            else:
                for i, r in enumerate(data["References"]):
                    if not isinstance(r, dict):
                        findings.append(_mk_lint(f"References[{i}]", "type_mismatch(object expected)", "use mapping"))
                        continue
                    for rk in ("doc", "section", "page", "para_id"):
                        if rk not in r:
                            findings.append(_mk_lint(f"References[{i}].{rk}", "missing", "add field"))

    # 5) M2.6 요약·표 최소 검증
    if is_m26:
        if "WrittenSummary" in data:
            ws = data["WrittenSummary"]
            if isinstance(ws, str):
                if len(ws) < 100:
                    findings.append(_mk_lint("WrittenSummary", "too_short(<100)", "expand narrative"))
            elif isinstance(ws, dict):
                blocks = (block.get("written_summary") or {}).get("blocks", [])
                for b in blocks:
                    bid = b.get("id")
                    min_len = b.get("min_len", 0)
                    if bid in ws and isinstance(ws[bid], str) and len(ws[bid]) < min_len:
                        findings.append(_mk_lint(f"WrittenSummary.{bid}", f"too_short(<{min_len})", "add details"))
            else:
                findings.append(_mk_lint("WrittenSummary", "type_mismatch(string or mapping expected)", "use string or {Block: text}"))

        if "TabulatedSummaries" in data:
            ts = data["TabulatedSummaries"]
            if not isinstance(ts, list):
                findings.append(_mk_lint("TabulatedSummaries", "type_mismatch(list expected)", "list of tables"))
            elif len(ts) == 0:
                findings.append(_mk_lint("TabulatedSummaries", "empty_list", "render at least one table"))

    ok = len(findings) == 0
    return ok, findings
