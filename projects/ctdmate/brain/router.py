# ctdmate/brain/router.py
from __future__ import annotations
import json
import re
from typing import Any, Dict, Optional

# 타입
try:
    from ctdmate.app.types import RoutePlan
except Exception:
    from typing import TypedDict
    class RoutePlan(TypedDict, total=False):
        action: str
        section: str
        need_parse: bool
        need_rag: bool
        need_generate: bool
        need_validate: bool
        output_format: str

# 프롬프트(있으면 사용)
try:
    from ctdmate.app.prompts import build_router_messages as _build_msgs  # type: ignore
    _HAS_PROMPTS = True
except Exception:
    _HAS_PROMPTS = False

# --------------------- Llama 로컬 클라이언트 스텁 ---------------------
class LlamaLocalClient:
    """
    로컬 Llama3.2-3B-instruct 호출 어댑터.
    llama.cpp / vLLM / transformers 어느 것이든 chat(system,user)만 구현하면 됨.
    """
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def chat(self, system: str, user: str) -> str:
        raise NotImplementedError("Implement local Llama call: client.chat(system, user) -> str(JSON)")

# --------------------- 유틸 ---------------------
_SECS = {"M1", "M2.3", "M2.4", "M2.5", "M2.6", "M2.7"}

def _normalize_section(s: str | None) -> str:
    if not s:
        return "UNKNOWN"
    s = s.strip().upper()
    return s if s.startswith("M") else f"M{s}"

def _coerce_section(s: str | None) -> str:
    c = _normalize_section(s)
    if c in _SECS:
        return c
    # 약식 숫자만 온 경우 근사 매핑
    if c in {"M23", "M-2.3", "2.3"}:
        return "M2.3"
    if c in {"M24", "2.4"}:
        return "M2.4"
    if c in {"M25", "2.5"}:
        return "M2.5"
    if c in {"M26", "2.6"}:
        return "M2.6"
    if c in {"M27", "2.7"}:
        return "M2.7"
    return "UNKNOWN"

def _bool(x: Any, default: bool = False) -> bool:
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return bool(x)
    if isinstance(x, str):
        t = x.strip().lower()
        if t in {"true", "yes", "y", "1"}:
            return True
        if t in {"false", "no", "n", "0"}:
            return False
    return default

def _fmt(x: Any) -> str:
    t = str(x or "").strip().lower()
    return "yaml" if t not in {"yaml", "markdown"} else t

def _safe_json(s: str) -> Dict[str, Any]:
    # 코드펜스 제거 후 첫 JSON 오브젝트 추출
    s = re.sub(r"^```(?:json)?|```$", "", s, flags=re.M).strip()
    m = re.search(r"\{.*\}", s, flags=re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}

def _heuristic_plan(desc: str) -> RoutePlan:
    d = (desc or "").lower()
    need_parse = any(w in d for w in ["pdf", "xlsx", "파일", "스캔", "ocr", "업로드"])
    need_generate = any(w in d for w in ["작성", "생성", "draft", "요약"])
    need_validate = any(w in d for w in ["검증", "체크", "lint", "validate", "적합성"])
    # 섹션 힌트
    sec = "UNKNOWN"
    if re.search(r"\bm2\.3\b|\bqos\b", d):
        sec = "M2.3"
    elif re.search(r"\bm2\.4\b|비임상\s*개요", d):
        sec = "M2.4"
    elif re.search(r"\bm2\.5\b|임상\s*개요", d):
        sec = "M2.5"
    elif re.search(r"\bm2\.6\b|비임상\s*요약", d):
        sec = "M2.6"
    elif re.search(r"\bm2\.7\b|임상\s*요약", d):
        sec = "M2.7"
    elif re.search(r"\bm1\b|행정|라벨", d):
        sec = "M1"

    action = "pipeline"
    if need_generate and not need_validate and not need_parse:
        action = "generate"
    elif need_validate and not need_generate:
        action = "validate"
    elif need_parse and not (need_generate or need_validate):
        action = "parse"

    return {
        "action": action,
        "section": sec,
        "need_parse": need_parse,
        "need_rag": True,
        "need_generate": need_generate,
        "need_validate": need_validate,
        "output_format": "yaml" if "yaml" in d else "markdown" if "markdown" in d else "yaml",
    }

def _merge(base: RoutePlan, llm_json: Dict[str, Any]) -> RoutePlan:
    out = dict(base)
    if not llm_json:
        return out  # LLM 실패 시 휴리스틱 유지
    if "action" in llm_json:
        out["action"] = str(llm_json["action"]).lower()
    if "section" in llm_json:
        out["section"] = _coerce_section(str(llm_json["section"]))
    if "need_parse" in llm_json:
        out["need_parse"] = _bool(llm_json["need_parse"], base.get("need_parse", False))
    if "need_rag" in llm_json:
        out["need_rag"] = _bool(llm_json["need_rag"], base.get("need_rag", True))
    if "need_generate" in llm_json:
        out["need_generate"] = _bool(llm_json["need_generate"], base.get("need_generate", False))
    if "need_validate" in llm_json:
        out["need_validate"] = _bool(llm_json["need_validate"], base.get("need_validate", False))
    if "output_format" in llm_json:
        out["output_format"] = _fmt(llm_json["output_format"])
    # 최종 보정
    out["section"] = _coerce_section(out.get("section"))
    if out["action"] not in {"generate", "validate", "parse", "pipeline"}:
        out["action"] = "pipeline"
    if out["output_format"] not in {"yaml", "markdown"}:
        out["output_format"] = "yaml"
    return out  # type: ignore[return-value]

# --------------------- Router ---------------------
class Router:
    """
    분기 뇌.
    1) 휴리스틱 초안 생성
    2) Llama3.2-3B가 JSON으로 최종 결론
    3) 병합·정규화 후 RoutePlan 반환
    """
    def __init__(self, llama: Optional[LlamaLocalClient] = None):
        self.llama = llama

    def decide(self, user_desc: str) -> RoutePlan:
        plan = _heuristic_plan(user_desc)

        if not self.llama:
            return plan

        try:
            if _HAS_PROMPTS:
                msgs = _build_msgs(user_desc)  # system + user(JSON 스키마)
                sys = msgs[0]["content"]; usr = msgs[1]["content"]
            else:
                sys = (
                    "당신은 CTD 작업 라우터다. action, section, need_parse, need_rag, "
                    "need_generate, need_validate, output_format 필드를 가진 JSON만 출력."
                )
                schema = {
                    "action": "generate|validate|parse|pipeline",
                    "section": "M1|M2.3|M2.4|M2.5|M2.6|M2.7|UNKNOWN",
                    "need_parse": True,
                    "need_rag": True,
                    "need_generate": False,
                    "need_validate": False,
                    "output_format": "yaml|markdown",
                }
                usr = f"입력 설명:\n{user_desc}\n\n아래 스키마로만 JSON을 출력하라:\n{json.dumps(schema, ensure_ascii=False)}"
            raw = self.llama.chat(system=sys, user=usr)
            j = _safe_json(raw)
            plan = _merge(plan, j)
        except Exception:
            # LLM 실패 시 휴리스틱만 사용
            pass

        return plan
