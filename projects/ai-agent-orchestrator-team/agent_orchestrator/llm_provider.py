#!/usr/bin/env python3
"""
LLM Provider Abstraction Layer
Supports easy switching between OpenAI GPT and LLaMA models
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

# Load .env file
try:
    from dotenv import load_dotenv
    # Find .env file in project root
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass  # python-dotenv not installed

logger = logging.getLogger(__name__)


@dataclass
class SummaryResult:
    """Result from summarization"""
    summary: str
    key_points: List[str]
    entities: List[str]
    action_items: List[str]
    confidence: float = 0.0


@dataclass
class PriorityAnalysis:
    """Result from priority analysis"""
    item_id: str
    priority_score: float  # 0-100
    urgency: str  # "urgent", "important", "normal", "low"
    category: str  # "email", "slack", "notion"
    reasoning: str
    estimated_time: Optional[str] = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    async def summarize_conversation(
        self,
        messages: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None
    ) -> SummaryResult:
        """
        Summarize a conversation with key points, entities, and action items

        Args:
            messages: List of message dicts with 'role' and 'text'
            context: Optional context information

        Returns:
            SummaryResult with summary, key_points, entities, action_items
        """
        pass

    @abstractmethod
    async def extract_insights(
        self,
        content: str,
        extract_type: str = "summary"
    ) -> SummaryResult:
        """
        Extract insights from text content

        Args:
            content: Text content to analyze
            extract_type: Type of extraction (summary, action_items, entities)

        Returns:
            SummaryResult with extracted insights
        """
        pass

    @abstractmethod
    async def analyze_priorities(
        self,
        items: List[Dict[str, Any]],
        context: Optional[str] = None
    ) -> List[PriorityAnalysis]:
        """
        Analyze and prioritize a list of items

        Args:
            items: List of items to prioritize (emails, tasks, messages)
            context: Optional context for prioritization

        Returns:
            List of PriorityAnalysis sorted by priority_score descending
        """
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT-based LLM provider (also supports OpenAI-compatible APIs like Upstage)"""

    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "gpt-4-turbo-preview",
        base_url: Optional[str] = None
    ):
        """
        Initialize OpenAI-compatible provider

        Args:
            api_key: API key (defaults to OPENAI_API_KEY env var)
            model: Model to use (gpt-4-turbo-preview, gpt-3.5-turbo, solar-pro2, etc.)
            base_url: Optional custom API endpoint for OpenAI-compatible services (e.g., Upstage)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key not provided. Set OPENAI_API_KEY or UPSTAGE_API_KEY environment variable.")

        self.model = model
        self.base_url = base_url
        
        if base_url:
            logger.info(f"Initialized OpenAI-compatible provider with model: {model}, base_url: {base_url}")
        else:
            logger.info(f"Initialized OpenAI provider with model: {model}")

        # Import OpenAI client
        try:
            from openai import AsyncOpenAI
            if base_url:
                self.client = AsyncOpenAI(api_key=self.api_key, base_url=base_url)
            else:
                self.client = AsyncOpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("openai package not installed. Run: uv add openai")

    async def summarize_conversation(
        self,
        messages: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None
    ) -> SummaryResult:
        """Summarize conversation using GPT"""
        logger.info(f"Summarizing conversation with {len(messages)} messages")

        # Format conversation for GPT
        conversation_text = "\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('text', '')}"
            for msg in messages
        ])

        # Add context if provided
        context_text = ""
        if context:
            context_text = f"\n\nContext:\n- Platform: {context.get('platform', 'unknown')}\n- Session: {context.get('session_id', 'unknown')}"

        prompt = f"""Analyze the following conversation and provide:
1. A concise summary (2-3 sentences)
2. Key points discussed (3-5 bullet points)
3. Entities mentioned (people, products, technologies, etc.)
4. Action items or next steps

Conversation:
{conversation_text}{context_text}

Return ONLY a JSON object with this structure:
{{
  "summary": "...",
  "key_points": ["...", "..."],
  "entities": ["...", "..."],
  "action_items": ["...", "..."]
}}"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that analyzes conversations and extracts structured insights. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            return SummaryResult(
                summary=result.get("summary", "No summary available"),
                key_points=result.get("key_points", []),
                entities=result.get("entities", []),
                action_items=result.get("action_items", []),
                confidence=0.9  # High confidence for GPT-4
            )

        except Exception as e:
            logger.error(f"Failed to summarize conversation: {e}")
            # Return fallback result
            return SummaryResult(
                summary=f"Conversation between {len(messages)} messages",
                key_points=["Analysis failed - fallback summary"],
                entities=[],
                action_items=[],
                confidence=0.0
            )

    async def extract_insights(
        self,
        content: str,
        extract_type: str = "summary"
    ) -> SummaryResult:
        """Extract insights from content using GPT"""
        logger.info(f"Extracting insights (type: {extract_type}) from content ({len(content)} chars)")

        prompts = {
            "summary": "Provide a comprehensive summary with key insights",
            "action_items": "Extract all action items and tasks mentioned",
            "entities": "Extract all entities (people, organizations, products, technologies)",
            "meeting_notes": "Summarize meeting notes with decisions and action items"
        }

        instruction = prompts.get(extract_type, prompts["summary"])

        prompt = f"""{instruction} from the following content:

{content[:4000]}  # Limit to prevent token overflow

Return ONLY a JSON object with this structure:
{{
  "summary": "...",
  "key_points": ["...", "..."],
  "entities": ["...", "..."],
  "action_items": ["...", "..."]
}}"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts structured insights from text. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            return SummaryResult(
                summary=result.get("summary", "No summary available"),
                key_points=result.get("key_points", []),
                entities=result.get("entities", []),
                action_items=result.get("action_items", []),
                confidence=0.9
            )

        except Exception as e:
            logger.error(f"Failed to extract insights: {e}")
            return SummaryResult(
                summary="Extraction failed",
                key_points=[],
                entities=[],
                action_items=[],
                confidence=0.0
            )

    async def analyze_priorities(
        self,
        items: List[Dict[str, Any]],
        context: Optional[str] = None
    ) -> List[PriorityAnalysis]:
        """Analyze and prioritize items using GPT"""
        logger.info(f"Analyzing priorities for {len(items)} items")

        if not items:
            return []

        # Format items for analysis
        items_text = json.dumps(items, indent=2, ensure_ascii=False)

        context_text = f"\n\nContext: {context}" if context else ""

        prompt = f"""다음 항목들을 분석하고 우선순위를 매겨주세요. 각 항목에 대해:
1. priority_score (0-100, 높을수록 긴급/중요)
2. urgency ("urgent", "important", "normal", "low")
3. category (항목 유형 기반)
4. reasoning (이 우선순위를 매긴 이유 - 한국어로 작성)
5. estimated_time (선택사항, 예: "5분", "1시간", "2시간")

분석할 항목:
{items_text}{context_text}

고려사항:
- 마감일과 시간 민감도
- 영향력과 중요도
- 다른 작업과의 의존성
- 발신자/출처의 권위

응답은 반드시 다음 JSON 형식으로만 작성:
{{
  "priorities": [
    {{
      "item_id": "...",
      "priority_score": 85,
      "urgency": "urgent",
      "category": "email",
      "reasoning": "한국어로 작성된 이유",
      "estimated_time": "30분"
    }}
  ]
}}"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 업무를 분석하고 우선순위를 매기는 어시스턴트입니다. 항상 유효한 JSON 형식으로 응답하며, reasoning은 한국어로 작성합니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            priorities = result.get("priorities", [])

            # Convert to PriorityAnalysis objects
            analyses = []
            for p in priorities:
                analyses.append(PriorityAnalysis(
                    item_id=p.get("item_id", "unknown"),
                    priority_score=float(p.get("priority_score", 50)),
                    urgency=p.get("urgency", "normal"),
                    category=p.get("category", "unknown"),
                    reasoning=p.get("reasoning", ""),
                    estimated_time=p.get("estimated_time")
                ))

            # Sort by priority_score descending
            analyses.sort(key=lambda x: x.priority_score, reverse=True)

            return analyses

        except Exception as e:
            logger.error(f"Failed to analyze priorities: {e}")
            # Return default priorities
            return [
                PriorityAnalysis(
                    item_id=item.get("id", f"item_{i}"),
                    priority_score=50.0,
                    urgency="normal",
                    category=item.get("category", "unknown"),
                    reasoning="Priority analysis failed - default priority assigned",
                    estimated_time=None
                )
                for i, item in enumerate(items)
            ]


class LlamaProvider(BaseLLMProvider):
    """LLaMA-based LLM provider using transformers"""

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize LLaMA provider

        Args:
            model_name: HuggingFace model name or local path (defaults to LLAMA_MODEL_PATH env var)
        """
        self.model_name = model_name or os.getenv("LLAMA_MODEL_PATH", "meta-llama/Llama-3.2-3B-Instruct")
        logger.info(f"Initializing LlamaProvider with model: {self.model_name}")

        # Import model loader
        try:
            from agent_orchestrator.model import load_model, generate_text
            self.generate_text = generate_text
        except ImportError:
            raise ImportError("model.py not found. Ensure agent_orchestrator/model.py exists.")

        # Load model and tokenizer
        self.tokenizer, self.model = load_model(self.model_name)
        logger.info("LlamaProvider initialized successfully")

    async def summarize_conversation(
        self,
        messages: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None
    ) -> SummaryResult:
        """Summarize conversation using Llama"""
        logger.info(f"Summarizing conversation with {len(messages)} messages using Llama")

        # Format conversation for Llama
        conversation_text = "\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('text', '')}"
            for msg in messages
        ])

        # Add context if provided
        context_text = ""
        if context:
            context_text = f"\n\nContext: {json.dumps(context, ensure_ascii=False)}"

        prompt = f"""다음 대화를 요약하고 주요 정보를 추출해주세요.

대화 내용:
{conversation_text}{context_text}

다음 항목을 JSON 형식으로 작성:
1. summary: 전체 대화 요약 (2-3문장, 한국어)
2. key_points: 핵심 포인트 리스트 (한국어)
3. entities: 언급된 주요 개체 (사람, 장소, 제품 등)
4. action_items: 해야 할 일 리스트 (한국어)

응답 형식:
{{
  "summary": "요약 내용",
  "key_points": ["포인트1", "포인트2"],
  "entities": ["개체1", "개체2"],
  "action_items": ["할일1", "할일2"]
}}

JSON:"""

        try:
            response = self.generate_text(
                self.tokenizer,
                self.model,
                prompt,
                max_new_tokens=800,
                temperature=0.3
            )

            # Parse JSON response
            result = json.loads(response)

            return SummaryResult(
                summary=result.get("summary", ""),
                key_points=result.get("key_points", []),
                entities=result.get("entities", []),
                action_items=result.get("action_items", []),
                confidence=0.8
            )

        except Exception as e:
            logger.error(f"Failed to summarize with Llama: {e}")
            return SummaryResult(
                summary="Summarization failed",
                key_points=[],
                entities=[],
                action_items=[],
                confidence=0.0
            )

    async def extract_insights(
        self,
        content: str,
        extract_type: str = "summary"
    ) -> SummaryResult:
        """Extract insights using Llama"""
        logger.info(f"Extracting insights (type: {extract_type}) using Llama")

        prompt = f"""다음 텍스트를 분석하고 인사이트를 추출해주세요.

텍스트:
{content}

추출 유형: {extract_type}

다음 항목을 JSON 형식으로 작성:
1. summary: 요약 (한국어)
2. key_points: 핵심 포인트 리스트 (한국어)
3. entities: 언급된 주요 개체
4. action_items: 실행 가능한 항목 (한국어)

응답 형식:
{{
  "summary": "요약 내용",
  "key_points": ["포인트1", "포인트2"],
  "entities": ["개체1", "개체2"],
  "action_items": ["할일1", "할일2"]
}}

JSON:"""

        try:
            response = self.generate_text(
                self.tokenizer,
                self.model,
                prompt,
                max_new_tokens=800,
                temperature=0.3
            )

            # Parse JSON response
            result = json.loads(response)

            return SummaryResult(
                summary=result.get("summary", ""),
                key_points=result.get("key_points", []),
                entities=result.get("entities", []),
                action_items=result.get("action_items", []),
                confidence=0.8
            )

        except Exception as e:
            logger.error(f"Failed to extract insights with Llama: {e}")
            return SummaryResult(
                summary="Extraction failed",
                key_points=[],
                entities=[],
                action_items=[],
                confidence=0.0
            )

    async def analyze_priorities(
        self,
        items: List[Dict[str, Any]],
        context: Optional[str] = None
    ) -> List[PriorityAnalysis]:
        """Analyze priorities using Llama"""
        logger.info(f"Analyzing priorities for {len(items)} items using Llama")

        # Format items for prompt
        items_text = ""
        for i, item in enumerate(items, 1):
            item_type = item.get("type", "unknown")
            if item_type == "email":
                subject = item.get("subject", "No subject")
                from_field = item.get("from", "Unknown")
                items_text += f"\n{i}. [Email] {subject} (from: {from_field})"
            elif item_type in ["slack_mention", "slack_dm"]:
                channel = item.get("channel", "Unknown")
                text = item.get("text", "")[:100]
                items_text += f"\n{i}. [Slack] {text} (in: {channel})"
            elif item_type == "notion_task":
                title = item.get("title", "No title")
                status = item.get("status", "")
                items_text += f"\n{i}. [Notion] {title} (status: {status})"
            else:
                items_text += f"\n{i}. {item.get('text', item.get('title', 'Unknown'))}"

        # Add context if provided
        context_text = ""
        if context:
            context_text = f"\n\n추가 컨텍스트:\n{context}"

        prompt = f"""다음 항목들을 분석하고 우선순위를 매겨주세요. 각 항목에 대해:
1. priority_score (0-100, 높을수록 긴급/중요)
2. urgency ("urgent", "important", "normal", "low")
3. category (항목 유형 기반)
4. reasoning (이 우선순위를 매긴 이유 - 한국어로 작성)
5. estimated_time (선택사항, 예: "5분", "1시간", "2시간")

분석할 항목:
{items_text}{context_text}

고려사항:
- 마감일과 시간 민감도
- 영향력과 중요도
- 다른 작업과의 의존성
- 발신자/출처의 권위

응답은 반드시 다음 JSON 형식으로만 작성:
{{
  "priorities": [
    {{
      "item_id": "...",
      "priority_score": 85,
      "urgency": "urgent",
      "category": "email",
      "reasoning": "한국어로 작성된 이유",
      "estimated_time": "30분"
    }}
  ]
}}

JSON:"""

        try:
            response = self.generate_text(
                self.tokenizer,
                self.model,
                prompt,
                max_new_tokens=1500,
                temperature=0.3
            )

            result = json.loads(response)
            priorities = result.get("priorities", [])

            # Convert to PriorityAnalysis objects
            analyses = []
            for p in priorities:
                analyses.append(PriorityAnalysis(
                    item_id=p.get("item_id", "unknown"),
                    priority_score=float(p.get("priority_score", 50)),
                    urgency=p.get("urgency", "normal"),
                    category=p.get("category", "unknown"),
                    reasoning=p.get("reasoning", ""),
                    estimated_time=p.get("estimated_time")
                ))

            # Sort by priority_score descending
            analyses.sort(key=lambda x: x.priority_score, reverse=True)

            return analyses

        except Exception as e:
            logger.error(f"Failed to analyze priorities with Llama: {e}")
            # Return default priorities
            return [
                PriorityAnalysis(
                    item_id=item.get("id", f"item_{i}"),
                    priority_score=50.0,
                    urgency="normal",
                    category=item.get("category", "unknown"),
                    reasoning="Priority analysis failed - default priority assigned",
                    estimated_time=None
                )
                for i, item in enumerate(items)
            ]


# Global cache for LLM provider (singleton pattern)
# This ensures we only load the model once per process
_llm_provider_cache: Optional[BaseLLMProvider] = None
_provider_lock = None

def get_llm_provider() -> BaseLLMProvider:
    """
    Factory function to get the configured LLM provider (with singleton caching)

    Returns:
        LLM provider instance based on LLM_PROVIDER env var
        Same instance is reused within a process to avoid loading model multiple times

    Environment Variables:
        LLM_PROVIDER: "openai", "upstage", or "llama" (default: llama)
        
        For OpenAI:
            OPENAI_API_KEY: Required
            OPENAI_MODEL: Optional, defaults to gpt-4-turbo-preview
        
        For Upstage (OpenAI-compatible):
            UPSTAGE_API_KEY: Required
            UPSTAGE_MODEL: Optional, defaults to solar-pro2
            UPSTAGE_BASE_URL: Optional, defaults to https://api.upstage.ai/v1/solar
        
        For LLaMA (via Ollama, OpenAI-compatible):
            OLLAMA_MODEL: Optional, defaults to llama3.2:3b
            OLLAMA_BASE_URL: Optional, defaults to http://localhost:11434/v1
            Note: Requires Ollama installed and running (https://ollama.com)
    """
    global _llm_provider_cache, _provider_lock
    
    # Return cached instance if available
    if _llm_provider_cache is not None:
        logger.debug("Reusing cached LLM provider instance")
        return _llm_provider_cache
    
    # Initialize lock if needed (for thread safety)
    if _provider_lock is None:
        import threading
        _provider_lock = threading.Lock()
    
    # Acquire lock to prevent multiple threads from loading simultaneously
    with _provider_lock:
        # Double-check after acquiring lock
        if _llm_provider_cache is not None:
            return _llm_provider_cache
        
        provider_type = os.getenv("LLM_PROVIDER", "llama").lower()
        logger.info(f"Initializing LLM provider: {provider_type} (will be cached for reuse)")

        if provider_type == "openai":
            model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
            _llm_provider_cache = OpenAIProvider(model=model)
        
        elif provider_type == "upstage":
            # Upstage uses OpenAI-compatible API, so we reuse OpenAIProvider
            api_key = os.getenv("UPSTAGE_API_KEY")
            if not api_key:
                raise ValueError("UPSTAGE_API_KEY environment variable not set")
            
            model = os.getenv("UPSTAGE_MODEL", "solar-pro2")
            base_url = os.getenv("UPSTAGE_BASE_URL", "https://api.upstage.ai/v1/solar")
            
            logger.info(f"Using Upstage provider with model: {model}")
            _llm_provider_cache = OpenAIProvider(api_key=api_key, model=model, base_url=base_url)
        
        elif provider_type == "llama":
            # LLaMA via Ollama (OpenAI-compatible API)
            # Ollama provides OpenAI-compatible API at http://localhost:11434/v1
            model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            
            # Ollama doesn't require API key, but OpenAI client needs one
            # Use dummy key "ollama" which Ollama ignores
            logger.info(f"Using Ollama provider with model: {model}, base_url: {base_url}")
            _llm_provider_cache = OpenAIProvider(api_key="ollama", model=model, base_url=base_url)
        
        else:
            raise ValueError(
                f"Unknown LLM_PROVIDER: {provider_type}. "
                f"Valid options: 'openai', 'upstage', 'llama'"
            )
        
        logger.info(f"LLM provider cached successfully (type: {type(_llm_provider_cache).__name__})")
        return _llm_provider_cache


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test_provider():
        # Get provider (will use OpenAI if OPENAI_API_KEY is set)
        llm = get_llm_provider()

        # Test conversation summarization
        messages = [
            {"role": "user", "text": "What's the best way to implement caching in Python?"},
            {"role": "assistant", "text": "There are several approaches: functools.lru_cache for function results, Redis for distributed caching, or memcached for simple key-value storage."},
            {"role": "user", "text": "Which one should I use for a web API?"},
            {"role": "assistant", "text": "For a web API, I'd recommend Redis because it's fast, supports various data structures, and works well in distributed environments."}
        ]

        result = await llm.summarize_conversation(messages)
        print("Summary:", result.summary)
        print("Key Points:", result.key_points)
        print("Entities:", result.entities)
        print("Action Items:", result.action_items)

    asyncio.run(test_provider())
