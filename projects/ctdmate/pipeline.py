# ctdmate/pipeline.py
from __future__ import annotations
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# 프로젝트 루트를 sys.path에 추가 (직접 실행 시)
if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

# config
try:
    from ctdmate.app import config as CFG
except Exception:
    from .app import config as CFG  # type: ignore

# types
try:
    from ctdmate.app.types import ParseOutput, ValidateExcelOutput, GenerateOutput, RoutePlan
except Exception:
    from .app.types import ParseOutput, ValidateExcelOutput, GenerateOutput, RoutePlan  # type: ignore

# brain
try:
    from ctdmate.brain.router import Router, LlamaLocalClient
except Exception:
    from .brain.router import Router, LlamaLocalClient  # type: ignore

# tools
try:
    from ctdmate.tools.smartdoc_upstage import run as parse_run
    from ctdmate.tools.reg_rag import RegulationRAGTool
    from ctdmate.tools.gen_solar import SolarGenerator
except Exception:
    from .tools.smartdoc_upstage import run as parse_run  # type: ignore
    from .tools.reg_rag import RegulationRAGTool  # type: ignore
    from .tools.gen_solar import SolarGenerator  # type: ignore


class CTDPipeline:
    """
    Router → Parse → Validate → Generate
    - Router: Llama3.2-3B가 action/section/format 결정
    - Parse: Upstage Document Parse → Markdown/JSONL
    - Validate: 규제 커버리지·신뢰도·위반 스코어 계산
    - Generate: Solar Pro2 + 인용형 RAG, Lint 게이트
    """

    def __init__(self, llama_client: Optional[LlamaLocalClient] = None, use_finetuned: bool = True):
        """
        Args:
            llama_client: 커스텀 Llama 클라이언트 (None이면 자동 생성)
            use_finetuned: Fine-tuned GGUF 모델 사용 여부 (기본: True)
        """
        # Fine-tuned 모델 자동 로드
        if llama_client is None and use_finetuned:
            try:
                from ctdmate.brain.llama_client import create_default_client
                llama_client = create_default_client(
                    n_ctx=2048,
                    n_gpu_layers=-1,  # GPU 전부 사용
                    temperature=0.1,
                    verbose=False,
                )
                print("✓ Fine-tuned GGUF model loaded successfully")
            except Exception as e:
                print(f"⚠️  Failed to load fine-tuned model: {e}")
                print("   Falling back to heuristic-only mode")
                llama_client = None

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

    def execute(
        self,
        user_desc: str,
        files: Optional[List[str]] = None,
        section: Optional[str] = None,
        output_format: Optional[str] = None,
        auto_fix: bool = True,
    ) -> Dict[str, Any]:
        plan: RoutePlan = self.router.decide(user_desc)
        if section:
            plan["section"] = section
        if output_format:
            plan["output_format"] = output_format

        # Parse
        parse_out: Optional[ParseOutput] = None
        if plan.get("need_parse") and files:
            parse_out = parse_run(files)

        # Validate
        validate_out: Optional[Dict[str, Any]] = None
        content_for_validate = user_desc

        # 입력 파일에서 Excel 검증 시도
        excel_file = None
        if files:
            for f in files:
                if str(f).lower().endswith(('.xlsx', '.xls')):
                    excel_file = f
                    break

        if plan.get("need_validate"):
            # Excel 파일이 있으면 Excel 검증 (Parse 성공 여부 무관)
            if excel_file:
                validate_out = self.reg_tool.validate_excel(str(excel_file), auto_fix=auto_fix)
            # Excel이 없으면 Parse 결과 또는 텍스트 단일 검증
            elif parse_out and parse_out.get("results"):
                # Parse 결과에서 첫 번째 markdown 사용
                content_for_validate = parse_out["results"][0].get("markdown", user_desc)
                validate_out = self.reg_tool.validate_and_normalize(
                    section=plan.get("section") or "M2.3",
                    content=content_for_validate,
                    auto_fix=auto_fix,
                )
            else:
                # Fallback: user_desc로 검증
                validate_out = self.reg_tool.validate_and_normalize(
                    section=plan.get("section") or "M2.3",
                    content=content_for_validate,
                    auto_fix=auto_fix,
                )

        # Decide gate for generation
        ok_for_gen = True
        normalized = user_desc

        # Extract normalized content and gate decision
        if isinstance(validate_out, dict):
            # Single validation result (validate_and_normalize)
            if "metrics" in validate_out:
                ok_for_gen = bool(validate_out["pass"]) and (
                    float(validate_out["metrics"]["score"]) >= CFG.GENERATE_GATE
                )
                normalized = validate_out.get("normalized_content") or user_desc
            # Excel validation result (validate_excel)
            elif "results" in validate_out and validate_out["results"]:
                # Combine all normalized content from sheets
                normalized_parts = []
                for sheet_result in validate_out["results"]:
                    if sheet_result.get("normalized_content"):
                        sheet_name = sheet_result.get("sheet_name", "Unknown")
                        normalized_parts.append(f"## {sheet_name}\n{sheet_result['normalized_content']}")

                if normalized_parts:
                    normalized = "\n\n".join(normalized_parts)

                # Use summary metrics for gate decision
                summary = validate_out.get("summary", {})
                avg_coverage = summary.get("avg_coverage", 0.0)
                pass_rate = summary.get("pass_rate", 0.0)
                score = 0.55 * avg_coverage + 0.45 * pass_rate
                ok_for_gen = score >= CFG.GENERATE_GATE

        # Generate
        generate_out: Optional[GenerateOutput] = None
        if plan.get("need_generate"):
            if ok_for_gen:
                generate_out = self.gen.generate(
                    section=plan.get("section") or "M2.3",
                    prompt=normalized,
                    output_format=plan.get("output_format") or "yaml",
                )
            else:
                generate_out = {  # type: ignore[assignment]
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
                }

        return {
            "plan": plan,
            "parse": parse_out,
            "validate": validate_out,
            "generate": generate_out,
        }

    def generate_all_modules(
        self,
        excel_path: str,
        output_dir: Optional[str] = None,
        auto_fix: bool = True,
    ) -> Dict[str, Any]:
        """
        Excel 파일의 모든 모듈(M1, M2.3-M2.7)에 대한 문서 생성

        Args:
            excel_path: Excel 파일 경로
            output_dir: 출력 디렉토리 (기본: generated_modules)
            auto_fix: 자동 정규화 활성화

        Returns:
            {
                'validate': ValidateExcelOutput,
                'generate': {module: {file, length, lint_ok, ready} | {error}}
            }
        """
        import json

        excel_file = Path(excel_path)
        if not excel_file.exists():
            raise FileNotFoundError(f"Excel 파일을 찾을 수 없습니다: {excel_path}")

        # 출력 디렉토리 설정
        if output_dir:
            out_dir = Path(output_dir)
        else:
            # ctdmate/input에서 실행하면 ctdmate/output으로, 아니면 기존 위치
            if "ctdmate" in str(excel_file.parent):
                out_dir = excel_file.parent.parent / "output"
            else:
                out_dir = excel_file.parent.parent / "generated_modules"
        out_dir.mkdir(exist_ok=True)

        # 1. Excel 전체 검증
        print("=" * 80)
        print("1단계: Excel 전체 검증")
        print("=" * 80)
        validate_result = self.reg_tool.validate_excel(str(excel_file), auto_fix=auto_fix)

        print(f"\n검증 결과:")
        print(f"  총 시트: {validate_result['total_sheets']}")
        print(f"  검증 시트: {validate_result['validated_sheets']}")
        print(f"  평균 Coverage: {validate_result['summary']['avg_coverage']:.2%}")
        print(f"  Pass Rate: {validate_result['summary']['pass_rate']:.2%}")

        # 2. 모듈별로 시트 그룹화
        module_sheets: Dict[str, List[Dict[str, Any]]] = {}
        for sheet in validate_result['results']:
            module = sheet['module']
            if module not in module_sheets:
                module_sheets[module] = []
            module_sheets[module].append(sheet)

        print(f"\n모듈 분포:")
        for module, sheets in sorted(module_sheets.items()):
            print(f"  {module}: {len(sheets)}개 시트")

        # 3. 각 모듈별로 문서 생성
        print("\n" + "=" * 80)
        print("2단계: 모듈별 문서 생성")
        print("=" * 80)

        all_results: Dict[str, Any] = {}

        for module in sorted(module_sheets.keys()):
            sheets = module_sheets[module]

            print(f"\n[{module}] 생성 중...")
            print(f"  시트: {', '.join([s['sheet_name'] for s in sheets])}")

            # 해당 모듈의 모든 시트 내용 결합
            combined_content = []
            for sheet in sheets:
                sheet_name = sheet['sheet_name']
                normalized = sheet.get('normalized_content', '')
                if normalized:
                    combined_content.append(f"## {sheet_name}\n{normalized}")

            if not combined_content:
                print(f"  ⚠️  내용 없음, 건너뜀")
                all_results[module] = {'error': 'No content'}
                continue

            content = "\n\n".join(combined_content)

            # 모듈별 문서 생성
            try:
                gen_result = self.gen.generate(
                    section=module,
                    prompt=content,
                    output_format="yaml",
                )

                # 파일 저장
                module_safe = module.replace(".", "_")
                output_file = out_dir / f"{module_safe}.yaml"
                output_file.write_text(gen_result['text'], encoding='utf-8')

                print(f"  ✓ 생성 완료: {output_file}")
                print(f"    - 길이: {len(gen_result['text'])} chars")
                print(f"    - Lint OK: {gen_result['lint_ok']}")
                print(f"    - Ready: {gen_result['ready']}")

                all_results[module] = {
                    'file': str(output_file),
                    'length': len(gen_result['text']),
                    'lint_ok': gen_result['lint_ok'],
                    'ready': gen_result['ready'],
                }

            except Exception as e:
                print(f"  ✗ 생성 실패: {e}")
                all_results[module] = {'error': str(e)}

        # 4. 최종 결과 요약
        print("\n" + "=" * 80)
        print("생성 완료 요약")
        print("=" * 80)

        success_count = sum(1 for r in all_results.values() if 'file' in r)
        print(f"\n성공: {success_count}/{len(all_results)} 모듈")

        for module in sorted(all_results.keys()):
            result = all_results[module]
            if 'file' in result:
                print(f"  ✓ {module:6} -> {result['file']} ({result['length']} chars)")
            else:
                print(f"  ✗ {module:6} -> Error: {result.get('error', 'Unknown')}")

        # 전체 결과 JSON 저장
        summary_file = out_dir / "generation_summary.json"
        summary_file.write_text(json.dumps({
            'validate': validate_result,
            'generate': all_results,
        }, ensure_ascii=False, indent=2), encoding='utf-8')

        print(f"\n전체 결과 저장: {summary_file}")

        return {
            'validate': validate_result,
            'generate': all_results,
        }


# CLI
def _read_text(p: Optional[str]) -> str:
    if not p:
        return ""
    path = Path(p)
    return path.read_text(encoding="utf-8") if path.exists() else p


if __name__ == "__main__":
    import argparse, json, sys

    # Load environment variables
    try:
        from dotenv import load_dotenv
        PROJECT_ROOT = Path(__file__).parent.parent
        env_file = PROJECT_ROOT / ".env.local"
        if env_file.exists():
            load_dotenv(str(env_file))
    except:
        pass

    ap = argparse.ArgumentParser(
        description="CTDMate pipeline: Router→Parse→Validate→Generate",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 전체 모듈 생성 (기본)
  python pipeline.py --all

  # 커스텀 Excel 파일로 전체 모듈 생성
  python pipeline.py --all --excel /path/to/file.xlsx

  # 단일 모듈 생성
  python pipeline.py -d "M2.3 문서 생성" -f input/CTD_bundle.xlsx -s M2.3

  # 검증만 실행
  python pipeline.py --validate-only -f input/CTD_bundle.xlsx
        """
    )

    # 모드 선택
    mode_group = ap.add_mutually_exclusive_group()
    mode_group.add_argument("--all", action="store_true", help="전체 모듈(M1, M2.3~M2.7) 문서 생성 (기본 모드)")
    mode_group.add_argument("--validate-only", action="store_true", help="검증만 실행 (문서 생성 안함)")

    # 전체 모듈 생성 옵션
    ap.add_argument("--excel", "-e", help="Excel 파일 경로 (기본: input/CTD_bundle.xlsx)")
    ap.add_argument("--output-dir", help="출력 디렉토리 (기본: output/)")

    # 단일 실행 옵션
    ap.add_argument("--desc", "-d", help="요청 설명 또는 프롬프트 텍스트/파일 경로")
    ap.add_argument("--files", "-f", nargs="*", help="파싱 대상 파일 목록(.pdf/.xlsx)")
    ap.add_argument("--section", "-s", help="강제 섹션(예: M2.3, M2.6, M2.7)")
    ap.add_argument("--format", "-o", choices=["yaml", "markdown"], help="출력 형식")
    ap.add_argument("--no-autofix", action="store_true", help="자동 정규화 비활성")

    args = ap.parse_args()

    pipe = CTDPipeline()

    # 모드 1: 전체 모듈 생성 (기본값 또는 --all)
    if args.all or (not args.desc and not args.validate_only):
        # Excel 파일 경로 결정
        if args.excel:
            excel_path = args.excel
        else:
            # ctdmate/input 우선, 없으면 tool1/input
            ctdmate_input = Path(__file__).parent / "input" / "CTD_bundle.xlsx"
            project_input = Path(__file__).parent.parent / "tool1" / "input" / "CTD_bundle.xlsx"

            if ctdmate_input.exists():
                excel_path = str(ctdmate_input)
            elif project_input.exists():
                excel_path = str(project_input)
            else:
                print(f"Error: Excel 파일을 찾을 수 없습니다.", file=sys.stderr)
                print(f"  시도한 경로:", file=sys.stderr)
                print(f"    - {ctdmate_input}", file=sys.stderr)
                print(f"    - {project_input}", file=sys.stderr)
                print(f"  --excel 옵션으로 경로를 지정하거나 input/CTD_bundle.xlsx를 생성하세요.", file=sys.stderr)
                sys.exit(1)

        # 전체 모듈 생성 실행
        result = pipe.generate_all_modules(
            excel_path=excel_path,
            output_dir=args.output_dir,
            auto_fix=not args.no_autofix,
        )

    # 모드 2: 검증만
    elif args.validate_only:
        if not args.files:
            print("Error: --validate-only는 -f/--files 옵션이 필요합니다.", file=sys.stderr)
            sys.exit(1)

        excel_file = next((f for f in args.files if f.endswith(('.xlsx', '.xls'))), None)
        if excel_file:
            result = pipe.reg_tool.validate_excel(excel_file, auto_fix=not args.no_autofix)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("Error: Excel 파일(.xlsx/.xls)을 찾을 수 없습니다.", file=sys.stderr)
            sys.exit(1)

    # 모드 3: 기존 단일 실행 모드
    elif args.desc:
        desc = _read_text(args.desc)
        out = pipe.execute(
            user_desc=desc,
            files=args.files or [],
            section=args.section,
            output_format=args.format,
            auto_fix=not args.no_autofix,
        )
        print(json.dumps(out, ensure_ascii=False, indent=2))

    else:
        ap.print_help()
        sys.exit(1)
