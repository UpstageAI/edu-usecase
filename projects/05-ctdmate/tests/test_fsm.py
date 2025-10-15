# ctdmate/tests/test_fsm.py
from __future__ import annotations
from ctdmate.app import fsm as fsm_mod

class FakeRegTool:
    def __init__(self, *a, **kw): ...
    def validate_and_normalize(self, section: str, content: str, auto_fix: bool = True):
        return {
            "validated": True,
            "pass": True,
            "normalized_content": content + " [norm]",
            "coverage": 0.8,
            "citations": [],
            "rag_conf": 0.7,
            "metrics": {"score": 0.85},
        }

class FakeGen:
    def __init__(self, *a, **kw): ...
    def generate(self, section: str, prompt: str, output_format: str = "yaml", csv_present=None):
        return {
            "section": section,
            "format": output_format,
            "text": "```yaml\nProductName: X\nReferences: []\n```",
            "rag_used": False,
            "rag_refs": [],
            "lint_ok": True,
            "lint_findings": [],
            "gen_metrics": {"gen_score": 1.0},
            "ready": True,
            "offline_fallback": None,
        }

def test_fsm_pipeline_without_parse(monkeypatch):
    # 외부 서비스 차단
    monkeypatch.setattr(fsm_mod, "RegulationRAGTool", FakeRegTool)
    monkeypatch.setattr(fsm_mod, "SolarGenerator", FakeGen)

    m = fsm_mod.CTDFSM(llama_client=None)
    out = m.run(desc="M2.7 임상 요약 작성 요청")
    assert out["ok"] is True
    assert out["generate"]["ready"] is True
    assert "ProductName" in out["generate"]["text"]
