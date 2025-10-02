# ctdmate/rag/term_normalizer.py
from __future__ import annotations
from typing import Any, Optional, Dict, List, Tuple
from pathlib import Path
import re, json, yaml

# config 경로 사용
try:
    from ctdmate.app import config as APP_CONFIG
except Exception:
    from ..app import config as APP_CONFIG  # type: ignore

_RULES: Optional[Dict[str, Any]] = None
_PATTERNS: List[Tuple[re.Pattern, str]] = []

def _read_text(p: Path) -> Optional[str]:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return None

def _load_rules() -> Dict[str, Any]:
    """normalization.yaml / normalize.json / nomalization.yaml 탐색 후 로드."""
    global _RULES, _PATTERNS
    if _RULES is not None:
        return _RULES

    candidates = [
        Path(APP_CONFIG.NORMALIZATION_PATH),
        Path(APP_CONFIG.RULES_DIR) / "normalization.yaml",
        Path(APP_CONFIG.RULES_DIR) / "normalize.json",
        Path(APP_CONFIG.RULES_DIR) / "nomalization.yaml",  # 오타 폴백
    ]

    data: Dict[str, Any] = {}
    for p in candidates:
        if p.exists():
            raw = _read_text(p)
            if not raw:
                continue
            try:
                data = yaml.safe_load(raw) if p.suffix.lower() in {".yaml", ".yml"} else json.loads(raw)
                if isinstance(data, dict):
                    break
            except Exception:
                continue

    terms: List[Dict[str, Any]] = []
    if isinstance(data.get("terms"), list):
        for t in data["terms"]:
            can = str(t.get("canonical", "")).strip()
            syns = [str(s).strip() for s in (t.get("synonyms") or []) if str(s).strip()]
            if can and syns:
                terms.append({"canonical": can, "synonyms": syns})
    elif isinstance(data.get("mappings"), dict):
        inv: Dict[str, List[str]] = {}
        for syn, can in data["mappings"].items():
            inv.setdefault(str(can), []).append(str(syn))
        for can, syns in inv.items():
            terms.append({"canonical": can, "synonyms": syns})
    else:
        for k, v in (data or {}).items():
            if isinstance(v, list):
                terms.append({"canonical": str(k), "synonyms": [str(s) for s in v]})

    _PATTERNS = []
    for t in terms:
        can = t["canonical"]
        for s in t["synonyms"]:
            _PATTERNS.append((re.compile(rf"(?<!\w){re.escape(s)}(?!\w)", re.I), can))

    _RULES = {"terms": terms}
    return _RULES

class TermNormalizer:
    """
    규칙 기반 용어 정규화기.
    - 규칙 파일 기반 치환
    - 선택: Llama3.2 클라이언트(client.chat(system,user))로 미세 보정
    """
    def __init__(self, client: Any = None):
        self.client = client
        _load_rules()

    def normalize(self, text: str) -> str:
        if not text:
            return text
        out = text
        for rx, can in _PATTERNS:
            out = rx.sub(can, out)
        if self.client:
            try:
                sys = "You normalize medical regulatory terms to canonical forms. Keep meaning. Return text only."
                user = f"Normalize terminology in Korean:\n{out}"
                resp = self.client.chat(system=sys, user=user)
                if isinstance(resp, str) and resp.strip():
                    out = resp.strip()
            except Exception:
                pass
        return out
