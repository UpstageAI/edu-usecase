# /workspace/src/core/router_client.py
from __future__ import annotations
import os, json, re, requests

JSON_GBNF = r'''
root        ::= "{" ws "\"tool\"" ws ":" ws tool ws "," ws "\"confidence\"" ws ":" ws number (ws "," ws "\"extra\"" ws ":" ws emptyobj)? ws "}"
tool        ::= "\"retrieve\"" | "\"web\"" | "\"answer\""
emptyobj    ::= "{" ws "}"
ws          ::= ([ \t\n\r])*
number      ::= int frac? exp?
int         ::= "0" | (digit19 digit*)
frac        ::= "." digit+
exp         ::= ("e" | "E") ("+" | "-")? digit+
digit       ::= [0-9]
digit19     ::= [1-9]
'''

_DEF_PROMPT = (
    '당신은 라우터입니다. 아래 중 하나만 JSON으로 출력하세요. 다른 텍스트 금지.\n'
    '형식: {"tool":"retrieve|web|answer","confidence":0.0~1.0,"extra":{}}\n'
)

class RouterClient:
    def __init__(self):
        self.url = os.getenv("ROUTER_URL", os.getenv("INFER_URL", "http://inference:8000")).rstrip("/")
        self.mode = os.getenv("ROUTER_MODE", "completion").lower()  # completion | openai
        self.max_tokens = int(os.getenv("ROUTER_MAX_TOKENS", "96"))
        self.temperature = float(os.getenv("ROUTER_TEMPERATURE", "0.01"))
        self.timeout = (10, 30)

    def _post(self, path, payload):
        r = requests.post(self.url + path, json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def _extract_json(self, text: str):
        m = re.search(r'\{.*\}', text, flags=re.S)
        if not m:
            raise ValueError("no-json-braces")
        return json.loads(m.group(0))  # 실패 시 예외로 던짐

    def classify_with_debug(self, query: str):
        dbg = {"router_mode": self.mode}
        if self.mode == "openai":
            payload = {
                "model": "router",
                "messages": [
                    {"role": "system", "content": _DEF_PROMPT},
                    {"role": "user", "content": query},
                ],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "response_format": {"type": "json_object"},
            }
            data = self._post("/v1/chat/completions", payload)
            text = data["choices"][0]["message"]["content"]
        else:
            prompt = _DEF_PROMPT + f'질문: "{query}"\n'
            payload = {
                "prompt": prompt,
                "n_predict": self.max_tokens,
                "temperature": self.temperature,
                "top_p": 0.95,
                "top_k": 40,
            }
            if os.getenv("ROUTER_USE_GRAMMAR", "1") == "1":
                payload["grammar"] = JSON_GBNF
                dbg["router_grammar"] = "on"
            data = self._post("/completion", payload)
            text = data.get("content") or data.get("content_raw") or ""

        dbg["router_raw"] = (text[:800] + "…") if len(text) > 800 else text

        try:
            out = self._extract_json(text)
            dbg["router_json_ok"] = True
        except Exception as e:
            dbg["router_json_ok"] = False
            dbg["router_json_error"] = str(e)
            # 안전한 폴백: retrieve로 진행
            out = {"tool": "retrieve", "confidence": 0.3, "extra": {}}

        tool = (out.get("tool") or "retrieve").lower()
        conf = float(out.get("confidence") or 0.5)
        extra = out.get("extra") or {}
        return {"tool": tool, "confidence": conf, "extra": extra, "_debug": dbg}
