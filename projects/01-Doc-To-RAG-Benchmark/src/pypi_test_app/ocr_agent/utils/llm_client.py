"""
LLM 클라이언트 (Upstage Solar pro2)
"""

import requests
import json
from typing import Dict, Any, Optional
from .. import config


class SolarClient:
    """Upstage Solar pro2 API 클라이언트"""
    
    def __init__(self):
        self.api_key = config.get_api_key()
        if not self.api_key:
            raise ValueError("SOLAR_API_KEY가 설정되지 않았습니다. 요청 헤더 또는 환경 변수를 확인하세요.")
        self.api_base = config.SOLAR_API_BASE
        self.model = config.SOLAR_MODEL
        self.max_tokens = config.SOLAR_MAX_TOKENS
        self.temperature = config.SOLAR_TEMPERATURE
    
    def call(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Solar pro2 API 호출
        
        Args:
            prompt: 사용자 프롬프트
            system: 시스템 프롬프트
            temperature: 온도 (기본값: config)
            max_tokens: 최대 토큰 (기본값: config)
            
        Returns:
            {
                "content": "응답 텍스트",
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "total_tokens": 150
                },
                "model": "solar-pro-2"
            }
        """
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        
        if system:
            messages.append({
                "role": "system",
                "content": system
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens
        }
        
        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=config.LLM_TIMEOUT
            )
            
            response.raise_for_status()
            
            data = response.json()
            
            # 응답 파싱
            choice = data["choices"][0]
            usage = data.get("usage", {})
            
            return {
                "content": choice["message"]["content"],
                "usage": {
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0)
                },
                "model": data.get("model", self.model)
            }
            
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Solar API error: {str(e)}")
            if hasattr(e, 'response') and e.response:
                print(f"응답: {e.response.text}")
            return None
        
        except Exception as e:
            print(f"[ERROR] Exception occurred: {str(e)}")
            return None


if __name__ == "__main__":
    # 테스트
    client = SolarClient()
    
    response = client.call(
        prompt="안녕하세요. Solar pro2 테스트입니다.",
        system="당신은 유용한 AI 어시스턴트입니다."
    )
    
    if response:
        print(f"[OK] Solar API call successful")
        print(f"응답: {response['content'][:100]}...")
        print(f"토큰: {response['usage']}")
    else:
        print(f"[ERROR] Solar API call failed")
