# ctdmate/tests/test_tools.py
from __future__ import annotations
from pathlib import Path
from ctdmate.tools.yaml_lint import lint_yaml
from ctdmate.tools.reg_rag import RegulationRAGTool

RULES_YAML = """
global_red_flags:
  phrases: ["TBD","as appropriate","etc."]

m2_3_qos:
  required: ["ProductName","DosageForm","ManufacturingProcess","References"]
  severities:
    ProductName: major
    DosageForm: minor
    ManufacturingProcess: major
    References: minor
  fields:
    ProductName:
      pattern: "^[A-Za-z0-9][A-Za-z0-9 \\-®™]{1,99}$"
    DosageForm:
      allowed_values_ref: "value_sets.DosageForm"
value_sets:
  DosageForm: ["Tablet","Capsule","Solution"]

m2_6:
  required_keys_base: ["WrittenSummary"]
  severities: {}
  policy:
    require_tabulated_if_csv: true
    require_written_if_no_csv: true
  written_summary:
    blocks:
      - {id: "Pharmacology", min_len: 10}
"""

def _write_rules(tmp_path: Path) -> str:
    p = tmp_path / "checklist.yaml"
    p.write_text(RULES_YAML, encoding="utf-8")
    return str(p)

def test_yaml_lint_m23_ok(tmp_path):
    rules = _write_rules(tmp_path)
    yml = """
    ProductName: ABC-1
    DosageForm: Tablet
    ManufacturingProcess: NEED_INPUT
    References:
      - {doc: ich_m4q, section: M2.3, page: 10, para_id: A}
    """
    ok, issues = lint_yaml(yaml_text=yml, section="M2.3", checklist_path=rules)
    assert ok is True
    assert issues == []

def test_yaml_lint_m26_branches(tmp_path):
    rules = _write_rules(tmp_path)
    # CSV 존재 → TabulatedSummaries 요구
    yml_csv = "WrittenSummary: 내용 충분합니다.\nTabulatedSummaries: [{}]"
    ok1, issues1 = lint_yaml(yaml_text=yml_csv, section="M2.6", csv_present=["m26_1_ex.csv"], checklist_path=rules)
    assert ok1 is True
    # CSV 미존재 → WrittenSummary 요구, 짧으면 실패
    yml_short = "WrittenSummary: 짧음"
    ok2, issues2 = lint_yaml(yaml_text=yml_short, section="M2.6", csv_present=None, checklist_path=rules)
    assert ok2 is False
    assert any("too_short" in (i.reason if hasattr(i, "reason") else i.get("reason","")) for i in issues2)

def test_reg_rag_metrics_present():
    # 외부 RAG 의존 끄고 최소 메트릭 확인
    reg = RegulationRAGTool(auto_normalize=False, enable_rag=False)
    res = reg.validate_and_normalize("M2.7", "임상 요약 텍스트. TBD")
    assert isinstance(res, dict)
    assert "metrics" in res
    assert "coverage" in res
    assert res["validated"] is True
