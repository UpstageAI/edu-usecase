# ctdmate/tests/test_router.py
from __future__ import annotations
from ctdmate.brain.router import Router, LlamaLocalClient

class NoopLlama(LlamaLocalClient):
    def chat(self, system: str, user: str) -> str:
        # 라우터 JSON 강제
        return (
            '{"action":"generate","section":"M2.7",'
            '"need_parse":false,"need_rag":true,'
            '"need_generate":true,"need_validate":true,"output_format":"yaml"}'
        )

def test_router_heuristic_only():
    r = Router(llama=None)
    plan = r.decide("M2.6 비임상 요약 작성 요청")
    assert plan["need_generate"] is True
    assert plan["section"] in {"M2.6", "UNKNOWN"}

def test_router_llama_override():
    r = Router(llama=NoopLlama())
    plan = r.decide("아무 설명")
    assert plan["action"] == "generate"
    assert plan["section"] == "M2.7"
    assert plan["output_format"] == "yaml"
