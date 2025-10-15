# ctdmate/app/router.py
from __future__ import annotations
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

# 내부 의존성
try:
    from ctdmate.app import config as CFG
    from ctdmate.app.fsm import CTDFSM
    from ctdmate.brain.router import Router, LlamaLocalClient
    from ctdmate.tools.reg_rag import RegulationRAGTool
    from ctdmate.tools.gen_solar import SolarGenerator
    from ctdmate.tools.smartdoc_upstage import run as parse_run
except Exception:
    from . import config as CFG  # type: ignore
    from .fsm import CTDFSM  # type: ignore
    from ..brain.router import Router, LlamaLocalClient  # type: ignore
    from ..tools.reg_rag import RegulationRAGTool  # type: ignore
    from ..tools.gen_solar import SolarGenerator  # type: ignore
    from ..tools.smartdoc_upstage import run as parse_run  # type: ignore

app = FastAPI(title="CTDMate API", version="0.1.0")

# 단일 인스턴스(간단)
_llama = LlamaLocalClient()  # 구현체로 교체
_router = Router(llama=_llama)
_fsm = CTDFSM(llama_client=_llama)
_reg = RegulationRAGTool(auto_normalize=True, enable_rag=True, llama_client=_llama)
_gen = SolarGenerator(enable_rag=True, auto_normalize=True, output_format="yaml")


# ---------- Pydantic 모델 ----------
class RouteReq(BaseModel):
    desc: str = Field(..., description="요청 설명")


class ParseReq(BaseModel):
    files: List[str] = Field(..., description="파싱 대상 경로(.pdf/.xlsx)")


class ValidateReq(BaseModel):
    section: Optional[str] = Field(None, description="예: M2.3, M2.6, M2.7")
    content: Optional[str] = Field(None, description="검증 텍스트")
    excel_path: Optional[str] = Field(None, description="엑셀 파일 경로. 제공 시 시트별 검증")
    auto_fix: bool = True


class GenerateReq(BaseModel):
    section: str = Field(..., description="예: M2.3, M2.6, M2.7")
    prompt: str = Field(..., description="생성 프롬프트")
    format: str = Field("yaml", pattern="^(yaml|markdown)$")
    csv_present: Optional[Any] = None


class PipelineReq(BaseModel):
    desc: str = Field(..., description="요청 설명 또는 프롬프트")
    files: Optional[List[str]] = None
    section: Optional[str] = None
    format: Optional[str] = Field(None, pattern="^(yaml|markdown)$")
    auto_fix: bool = True


# ---------- 라우트 ----------
@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": "ctdmate",
        "version": app.version,
        "qdrant_url": CFG.QDRANT_URL,
        "embed_model": CFG.EMBED_MODEL,
        "upstage_model": CFG.UPSTAGE_MODEL,
    }


@app.post("/v1/route")
def route(req: RouteReq) -> Dict[str, Any]:
    return _router.decide(req.desc)


@app.post("/v1/parse")
def parse(req: ParseReq) -> Dict[str, Any]:
    return parse_run(req.files)


@app.post("/v1/validate")
def validate(req: ValidateReq) -> Dict[str, Any]:
    if req.excel_path:
        return _reg.validate_excel(req.excel_path, auto_fix=req.auto_fix)
    section = req.section or "M2.3"
    content = req.content or ""
    return _reg.validate_and_normalize(section=section, content=content, auto_fix=req.auto_fix)


@app.post("/v1/generate")
def generate(req: GenerateReq) -> Dict[str, Any]:
    return _gen.generate(section=req.section, prompt=req.prompt, output_format=req.format, csv_present=req.csv_present)


@app.post("/v1/pipeline")
def pipeline(req: PipelineReq) -> Dict[str, Any]:
    return _fsm.run(
        desc=req.desc,
        files=req.files or [],
        section=req.section,
        output_format=req.format,
        auto_fix=req.auto_fix,
    )


# ---------- 로컬 실행 ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ctdmate.app.router:app", host="0.0.0.0", port=8000, reload=False)
