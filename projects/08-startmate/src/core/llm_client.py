# src/core/llm_client.py
from __future__ import annotations
import os, json, requests
from typing import Any, Dict, List, Optional

class LLMClient:
    def __init__(self):
        self.provider = os.getenv("MODEL_PROVIDER", "upstage")
        self.api_key  = os.getenv("UPSTAGE_API_KEY", "")
        # 기본값을 /v1/solar 로
        self.base     = (os.getenv("UPSTAGE_BASE_URL", "https://api.upstage.ai/v1/solar")).rstrip("/")
        self.model    = os.getenv("UPSTAGE_MODEL", "solar-1-mini-chat")
        self.timeout  = float(os.getenv("LLM_HTTP_TIMEOUT", "60"))

    # --- Public --------------------------------------------------------------
    def generate_text(self, prompt: str, max_tokens: int = 512, temperature: float = 0.3) -> str:
        """
        일반 텍스트 생성: Chat Completions 형식으로 messages 배열 전송
        """
        return self._upstage_chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )

    def generate_json(self, prompt: str, max_tokens: int = 256) -> Dict[str, Any]:
        """
        JSON mode 강제 (router 용)
        """
        txt = self._upstage_chat(
            messages=[
                {"role": "system", "content": "You must reply with a single JSON object. No extra text."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        try:
            return json.loads(txt)
        except Exception:
            # 실패시 최대한 회복
            start = txt.find("{")
            end   = txt.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(txt[start:end+1])
            raise

    # --- Internal ------------------------------------------------------------
    def _upstage_chat(
        self,
        *,
        messages: List[Dict[str, Any]],
        max_tokens: int,
        temperature: float = 0.3,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        assert self.api_key, "UPSTAGE_API_KEY missing"
        url = f"{self.base}/chat/completions"  # ← /v1/solar/chat/completions
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if response_format:
            body["response_format"] = response_format

        r = requests.post(url, headers=headers, json=body, timeout=self.timeout)
        # 400 디버그에 도움 되도록 상세 로그 포함
        if r.status_code >= 400:
            raise requests.HTTPError(
                f"{r.status_code} error from Upstage: {r.text}\n"
                f"URL={url}\nBODY={json.dumps(body, ensure_ascii=False)[:1200]}",
                response=r
            )
        data = r.json()
        return data["choices"][0]["message"]["content"]
