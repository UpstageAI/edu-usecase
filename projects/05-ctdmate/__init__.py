# ctdmate/__init__.py
from __future__ import annotations

# 공개 경로
from .pipeline import CTDPipeline

# 하위 패키지 re-export (선택)
from . import app as app
from . import brain as brain
from . import tools as tools
from . import rag as rag
from . import ui as ui

__all__ = [
    "CTDPipeline",
    "app",
    "brain",
    "tools",
    "rag",
    "ui",
]
