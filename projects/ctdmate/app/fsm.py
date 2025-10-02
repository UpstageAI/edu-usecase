# ctdmate/app/fsm.py
from __future__ import annotations
from enum import Enum, auto
from typing import Any, Dict, List, Optional

# 내부 의존성
try:
    from ctdmate.app import config as CFG
except Exception:
    from . import config as CFG  # type: ignore

try:
    from ctdmate.brain.router import Router, LlamaLocalClient
    from ctdmate.tools.smartdoc_upstage import run as parse_run
    from ctdmate.tools.reg_rag import RegulationRAGTool
    from ctdmate.tools.gen_solar import SolarGenerator
except Exception:
    from ..brain.router import Router, LlamaLocalClient  # type: ignore
    from ..tools.smartdoc_upstage import run as parse_run  # type: ignore
    from ..tools.reg_rag import RegulationRAGTool  # type: ignore
    from ..tools.gen_solar import SolarGenerator  # type: ignore


class CTDState(Enum):
    ROUTE = auto()
    PARSE = auto()
    VALIDATE = auto()
    GENERATE = auto()
    DONE = auto()
    ERROR = auto()


class CTDFSM:
    """
    단순 FSM 오케스트레이터.
    ROUTE → (PARSE) → (VALIDATE) → (GENERATE) → DONE
    """

    def __init__(self, llama_client: Optional[LlamaLocalClient] = None):
        self.router = Router(llama=llama_client)
        self.reg_tool = RegulationRAGTool(
            auto_normalize=True,
            enable_rag=True,
            llama_client=llama_client,
        )
        self.gen = SolarGenerator(
            enable_rag=True,
            auto_normalize=True,
            output_format="yaml",
        )

    def plan(self, desc: str) -> Dict[str, Any]:
        return self.router.decide(desc)

    def step_parse(self, files: Optional[List[str]]) -> Optional[Dict[str, Any]]:
        if not files:
            return None
        return parse_run(files)

    def step_validate(
        self,
        plan: Dict[str, Any],
        user_desc: str,
        parse_out: Optional[Dict[str, Any]],
        auto_fix: bool = True,
    ) -> Optional[Dict[str, Any]]:
        # 엑셀 시트가 있으면 엑셀 우선 검증
        if parse_out and parse_out.get("results"):
            for r in parse_out["results"]:
                if str(r["input"]).lower().endswith(".xlsx"):
                    return self.reg_tool.validate_excel(r["input"], auto_fix=auto_fix)
        # 텍스트 단일 검증
        if plan.get("need_validate", True):
            return self.reg_tool.validate_and_normalize(
                section=plan.get("section") or "M2.3",
                content=user_desc,
                auto_fix=auto_fix,
            )
        return None

    def step_generate(
        self,
        plan: Dict[str, Any],
        validate_out: Optional[Dict[str, Any]],
        user_desc: str,
    ) -> Optional[Dict[str, Any]]:
        if not plan.get("need_generate"):
            return None

        ok_for_gen = True
        normalized = user_desc
        if isinstance(validate_out, dict) and "metrics" in validate_out:
            ok_for_gen = bool(validate_out.get("pass")) and (
                float(validate_out["metrics"]["score"]) >= CFG.GENERATE_GATE
            )
            normalized = validate_out.get("normalized_content") or user_desc

        if not ok_for_gen:
            return {
                "section": plan.get("section") or "M2.3",
                "format": plan.get("output_format") or "yaml",
                "text": "",
                "rag_used": False,
                "rag_refs": [],
                "lint_ok": False,
                "lint_findings": [],
                "gen_metrics": {"gen_score": 0.0},
                "ready": False,
                "offline_fallback": None,
                "skipped": True,
                "reason": "gate_not_met",
                "thresholds": {
                    "generate_gate": CFG.GENERATE_GATE,
                },
            }

        return self.gen.generate(
            section=plan.get("section") or "M2.3",
            prompt=normalized,
            output_format=plan.get("output_format") or "yaml",
        )

    def run(
        self,
        desc: str,
        files: Optional[List[str]] = None,
        section: Optional[str] = None,
        output_format: Optional[str] = None,
        auto_fix: bool = True,
    ) -> Dict[str, Any]:
        state = CTDState.ROUTE
        out: Dict[str, Any] = {"trace": []}

        try:
            # ROUTE
            plan = self.plan(desc)
            if section:
                plan["section"] = section
            if output_format:
                plan["output_format"] = output_format
            out["plan"] = plan
            out["trace"].append({"state": state.name, "ok": True})

            # PARSE
            state = CTDState.PARSE
            parse_out = self.step_parse(files) if plan.get("need_parse") else None
            out["parse"] = parse_out
            out["trace"].append({"state": state.name, "ok": True, "pages": (parse_out or {}).get("results") and sum(r.get("pages", 0) for r in parse_out["results"]) or 0})

            # VALIDATE
            state = CTDState.VALIDATE
            val_out = self.step_validate(plan, desc, parse_out, auto_fix=auto_fix) if plan.get("need_validate", True) else None
            out["validate"] = val_out
            out["trace"].append({"state": state.name, "ok": True})

            # GENERATE
            state = CTDState.GENERATE
            gen_out = self.step_generate(plan, val_out, desc) if plan.get("need_generate") else None
            out["generate"] = gen_out
            out["trace"].append({"state": state.name, "ok": True})

            # DONE
            state = CTDState.DONE
            out["trace"].append({"state": state.name, "ok": True})
            out["ok"] = True
            return out

        except Exception as e:
            out["ok"] = False
            out["error"] = str(e)
            out["trace"].append({"state": CTDState.ERROR.name, "ok": False, "error": str(e)})
            return out
