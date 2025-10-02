# ctdmate/app/prompts.py
from __future__ import annotations
from typing import List, Dict, Any, Tuple
import json
import re
from textwrap import dedent

# ------------------------------------------------------------
# 공통 유틸
# ------------------------------------------------------------
def _normalize_section(s: str) -> str:
    s = (s or "").strip().upper()
    return s if s.startswith("M") else f"M{s}"

def render_context_refs(refs: List[Dict[str, Any]], max_len: int = 300) -> str:
    """
    refs: [{"doc","section","page","snippet"}]
    콘텍스트 블록을 [CIT-i] 라벨로 묶어 생성.
    """
    out = []
    for i, r in enumerate(refs or [], 1):
        doc = r.get("doc", "N/A")
        sec = r.get("section", "N/A")
        page = r.get("page", "N/A")
        snip = (r.get("snippet") or "").strip()
        if len(snip) > max_len:
            snip = snip[:max_len] + "..."
        out.append(f"[CIT-{i}] doc={doc} section={sec} page={page}\nSNIPPET: {snip}")
    return "\n\n".join(out) if out else "N/A"

# ------------------------------------------------------------
# Router(Llama3.2-3B) 프롬프트
# ------------------------------------------------------------
ROUTER_SYSTEM = dedent("""
당신은 제약 인허가(CTD) 작업 라우터다. 입력 설명을 분석해 다음 JSON 스키마로만 응답한다.
필드: action, section, need_parse, need_rag, need_generate, need_validate, output_format.
규칙:
- 원문 파일 언급 시 need_parse=true
- CTD 초안/요약 작성 요청 시 need_generate=true, need_rag=true
- 검증/체크/린트 요청 시 need_validate=true
- section은 {M1,M2.3,M2.4,M2.5,M2.6,M2.7} 중 최적 후보
- 출력은 JSON 한 덩어리. 여분 텍스트 금지
""").strip()

def router_user(desc: str) -> str:
    schema = {
        "action": "generate|validate|parse|pipeline",
        "section": "M1|M2.3|M2.4|M2.5|M2.6|M2.7|UNKNOWN",
        "need_parse": True,
        "need_rag": True,
        "need_generate": False,
        "need_validate": False,
        "output_format": "yaml|markdown"
    }
    return dedent(f"""
    입력 설명:
    {desc}

    위 설명을 바탕으로 아래 스키마에 맞춘 JSON만 출력하라:
    {json.dumps(schema, ensure_ascii=False, indent=2)}
    """).strip()

# ------------------------------------------------------------
# Generator(Solar Pro2) 프롬프트
# ------------------------------------------------------------
def gen_system(section: str, language: str = "ko") -> str:
    sec = _normalize_section(section)
    return dedent(f"""
    역할: 제약 인허가 문서 CTD {sec} 초안 작성 에이전트.
    원칙:
    - 제공된 Context 안에서만 사실 인용. 추정 금지.
    - 핵심 문장 말미에 [CIT-1],[CIT-2] 형식 인용 태그 부착.
    - 출력 형식은 지시한 한 가지(YAML 또는 Markdown)만 사용.
    - 용어·단위·축약은 ICH/MFDS 표기. 한국어({language}) 유지.
    - 불명확한 값은 NEED_INPUT.
    """).strip()

def gen_instruction_yaml(section: str, skeleton_hint: Dict[str, Any] | None = None) -> str:
    sec = _normalize_section(section)
    hint = json.dumps(skeleton_hint or {"References": []}, ensure_ascii=False, indent=2)
    return dedent(f"""
    1) CTD {sec} 스켈레톤을 준수해 YAML을 생성하라.
    2) 각 핵심 문장에 [CIT-i] 인용 표기를 남겨라.
    3) 최하단에 References: - {{doc, section, page, para_id}} 리스트를 포함하라.
    4) 불명확한 값은 "NEED_INPUT".
    5) 결과 전체를 ```yaml 코드펜스```로 감싸라.
    스켈레톤 힌트:
    {hint}
    """).strip()

def gen_instruction_md(section: str) -> str:
    sec = _normalize_section(section)
    return dedent(f"""
    1) CTD {sec} 섹션을 Markdown으로 작성하라.
    2) 각 핵심 문장에 [CIT-i] 인용 표기를 남겨라.
    3) 문서 끝에 '## References' 섹션과 - doc | section | page | para_id 목록을 추가하라.
    4) 불명확한 값은 NEED_INPUT.
    """).strip()

def gen_user_block(user_prompt: str, ctx_refs: List[Dict[str, Any]]) -> str:
    ctx = render_context_refs(ctx_refs)
    return dedent(f"""
    사용자 요청:
    {user_prompt.strip()}

    Context(인용 원문):
    {ctx}
    """).strip()

# ------------------------------------------------------------
# Normalizer(Llama3.2-3B 보정) 프롬프트
# ------------------------------------------------------------
NORMALIZER_SYSTEM = "You normalize medical regulatory terms to canonical forms. Keep meaning. Return text only."
def normalizer_user(text: str) -> str:
    return f"Normalize terminology in Korean:\n{text.strip()}"

# ------------------------------------------------------------
# Validator(선택 LLM 보조) 프롬프트
#  - 현재 규칙 기반 검증이 주. 필요 시 사용.
# ------------------------------------------------------------
VALIDATOR_SYSTEM = dedent("""
당신은 CTD 규제 검사 보조다. 텍스트에서 placeholder(TBD/미정/etc.), 금칙어, 포맷 위반 사례를 목록으로만 나열한다.
각 항목은 {"field","issue","hint"} 키를 가진 JSON 배열로만 응답한다.
""").strip()

def validator_user(section: str, text: str) -> str:
    sec = _normalize_section(section)
    return dedent(f"""
    섹션: {sec}
    검사대상:
    {text}
    """).strip()

# ------------------------------------------------------------
# 메시지 빌더(선택 사용)
# ------------------------------------------------------------
def build_router_messages(desc: str) -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": ROUTER_SYSTEM},
        {"role": "user", "content": router_user(desc)},
    ]

def build_gen_messages(
    section: str,
    user_prompt: str,
    ctx_refs: List[Dict[str, Any]],
    want_yaml: bool,
    skeleton_hint: Dict[str, Any] | None = None,
    language: str = "ko",
) -> List[Dict[str, str]]:
    sys = gen_system(section, language=language)
    inst = gen_instruction_yaml(section, skeleton_hint) if want_yaml else gen_instruction_md(section)
    usr = gen_user_block(user_prompt, ctx_refs)
    return [
        {"role": "system", "content": sys},
        {"role": "user", "content": inst},
        {"role": "user", "content": usr},
    ]
