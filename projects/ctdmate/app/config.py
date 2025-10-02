# ctdmate/app/config.py
from __future__ import annotations
import os
from pathlib import Path

# ---------- Paths ----------
ROOT_DIR = Path(__file__).resolve().parents[1]
RULES_DIR = ROOT_DIR / "rules"

def _first_existing(paths):
    for p in paths:
        if Path(p).exists():
            return str(Path(p))
    return str(paths[-1])

NORMALIZATION_PATH = _first_existing([
    RULES_DIR / "normalization.yaml",
    RULES_DIR / "normalize.json",
    RULES_DIR / "nomalization.yaml",   # legacy typo fallback
])

CHECKLIST_PATH = _first_existing([
    RULES_DIR / "checklist.yaml",
])

# ---------- Thresholds (env override-able) ----------
COVERAGE_MIN   = float(os.getenv("CTD_COVERAGE_MIN", "0.70"))
RAG_CONF_MIN   = float(os.getenv("CTD_RAG_CONF_MIN", "0.40"))
VIO_MAX        = int(os.getenv("CTD_VIO_MAX", "3"))          # weighted violations
GENERATE_GATE  = float(os.getenv("CTD_GENERATE_GATE", "0.65"))
LINT_MAX_MAJOR = int(os.getenv("CTD_LINT_MAX_MAJOR", "0"))   # allow zero major/critical
GENERATE_READY_MIN = float(os.getenv("CTD_GENERATE_READY_MIN", "0.70"))

# ---------- External services ----------
UPSTAGE_API_BASE = os.getenv("UPSTAGE_API_BASE", "https://api.upstage.ai/v1")
UPSTAGE_MODEL    = os.getenv("UPSTAGE_MODEL", "solar-pro2")
UPSTAGE_CHAT_PATH= os.getenv("UPSTAGE_CHAT_PATH", "/solar/chat/completions")
UPSTAGE_API_KEY  = os.getenv("UPSTAGE_API_KEY", "up_X7mV85DcfWE2eL1b6FQ57CKTQKUqh")
EMBED_MODEL      = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-large-instruct")
QDRANT_URL       = os.getenv("QDRANT_URL", "")  # 빈 문자열 = 로컬 path 모드
QDRANT_API_KEY   = os.getenv("QDRANT_API_KEY", "")
QDRANT_GUIDE_COLLECTION    = os.getenv("QDRANT_GUIDE_COLLECTION", "guidelines")
QDRANT_GLOSSARY_COLLECTION = os.getenv("QDRANT_GLOSSARY_COLLECTION", "glossary")
