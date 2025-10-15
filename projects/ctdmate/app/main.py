# ctdmate/app/main.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

def _read_text(p: Optional[str]) -> str:
    if not p:
        return ""
    path = Path(p)
    return path.read_text(encoding="utf-8") if path.exists() else p

# deps
try:
    from ctdmate.app.fsm import CTDFSM
    from ctdmate.brain.router import Router, LlamaLocalClient
    from ctdmate.tools.smartdoc_upstage import run as parse_run
    from ctdmate.tools.reg_rag import RegulationRAGTool
    from ctdmate.tools.gen_solar import SolarGenerator
except Exception:
    from .fsm import CTDFSM  # type: ignore
    from ..brain.router import Router, LlamaLocalClient  # type: ignore
    from ..tools.smartdoc_upstage import run as parse_run  # type: ignore
    from ..tools.reg_rag import RegulationRAGTool  # type: ignore
    from ..tools.gen_solar import SolarGenerator  # type: ignore

def main():
    import argparse, os
    ap = argparse.ArgumentParser(prog="ctdmate", description="CTDMate CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_route = sub.add_parser("route");        p_route.add_argument("--desc", "-d", required=True)
    p_parse = sub.add_parser("parse");        p_parse.add_argument("files", nargs="+")
    p_val   = sub.add_parser("validate")
    p_val.add_argument("--section", "-s", default="M2.3")
    p_val.add_argument("--content", "-c")
    p_val.add_argument("--excel", "-x")
    p_val.add_argument("--no-autofix", action="store_true")

    p_gen   = sub.add_parser("generate")
    p_gen.add_argument("--section", "-s", required=True)
    p_gen.add_argument("--prompt", "-p", required=True)
    p_gen.add_argument("--format", "-f", default="yaml", choices=["yaml","markdown"])

    p_pipe  = sub.add_parser("pipeline")
    p_pipe.add_argument("--desc", "-d", required=True)
    p_pipe.add_argument("--files", "-f", nargs="*")
    p_pipe.add_argument("--section", "-s")
    p_pipe.add_argument("--format", "-o", choices=["yaml","markdown"])
    p_pipe.add_argument("--no-autofix", action="store_true")

    p_srv   = sub.add_parser("serve")
    p_srv.add_argument("--host", default=os.getenv("HOST","0.0.0.0"))
    p_srv.add_argument("--port", type=int, default=int(os.getenv("PORT","8000")))
    p_srv.add_argument("--reload", action="store_true")

    args = ap.parse_args()

    llama = LlamaLocalClient()  # 구현체로 교체 가능
    if args.cmd == "route":
        out = Router(llama=llama).decide(_read_text(args.desc))
        print(json.dumps(out, ensure_ascii=False, indent=2)); return

    if args.cmd == "parse":
        out = parse_run(args.files)
        print(json.dumps(out, ensure_ascii=False, indent=2)); return

    if args.cmd == "validate":
        reg = RegulationRAGTool(auto_normalize=True, enable_rag=True, llama_client=llama)
        if args.excel:
            out = reg.validate_excel(args.excel, auto_fix=not args.no_autofix)
        else:
            out = reg.validate_and_normalize(args.section, _read_text(args.content), auto_fix=not args.no_autofix)
        print(json.dumps(out, ensure_ascii=False, indent=2)); return

    if args.cmd == "generate":
        gen = SolarGenerator(enable_rag=True, auto_normalize=True, output_format=args.format)
        out = gen.generate(section=args.section, prompt=_read_text(args.prompt), output_format=args.format)
        print(out["text"])
        meta = {k:v for k,v in out.items() if k != "text"}
        print("\n---\nMETA:\n" + json.dumps(meta, ensure_ascii=False, indent=2))
        return

    if args.cmd == "pipeline":
        fsm = CTDFSM(llama_client=llama)
        out = fsm.run(
            desc=_read_text(args.desc),
            files=args.files or [],
            section=args.section,
            output_format=args.format,
            auto_fix=not args.no_autofix,
        )
        print(json.dumps(out, ensure_ascii=False, indent=2)); return

    if args.cmd == "serve":
        import uvicorn
        uvicorn.run("ctdmate.app.router:app", host=args.host, port=args.port, reload=args.reload); return

if __name__ == "__main__":
    main()
