# core/debug.py
from __future__ import annotations
import json, os, sys, time

DEBUG_ON = os.getenv("DEBUG", "0") == "1"

def log(event: str, **fields):
    """터미널로 JSON 라인 출력 (DEBUG=1에서만)."""
    if not DEBUG_ON:
        return
    rec = {"ts": int(time.time()*1000), "event": event}
    rec.update(fields)
    print(json.dumps(rec, ensure_ascii=False), file=sys.stdout, flush=True)

def set_field(state, name: str, value):
    """Pydantic State에 안전하게 쓰기(필드 없으면 조용히 무시)."""
    try:
        setattr(state, name, value)
    except Exception:
        pass
