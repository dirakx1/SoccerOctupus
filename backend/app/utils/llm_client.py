"""
LLM client — OpenAI-compatible endpoint (identical pattern to MiroFish).
"""

import json
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI

from ..config import Config
from ..runtime_settings import RuntimeSettings


class LLMClient:
    def __init__(
        self,
        settings: Optional[RuntimeSettings] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        runtime = settings
        self.api_key = api_key or (runtime.llm_api_key if runtime else Config.LLM_API_KEY)
        self.base_url = base_url or (runtime.llm_base_url if runtime else Config.LLM_BASE_URL)
        self.model = model or (runtime.llm_model_name if runtime else Config.LLM_MODEL_NAME)

        if not self.api_key:
            raise ValueError("LLM_API_KEY is not set")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        try:
            response = self.client.chat.completions.create(**kwargs)
        except Exception as exc:
            # Some models (e.g. claude-opus-4-8 via Anthropic's OpenAI-compatible
            # endpoint) have deprecated the temperature parameter.
            if "temperature" in str(exc).lower() and "deprecated" in str(exc).lower():
                kwargs.pop("temperature", None)
                response = self.client.chat.completions.create(**kwargs)
            else:
                raise
        content = response.choices[0].message.content or ""
        # Strip <think> blocks some models emit
        content = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()
        return content

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", response.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM returned invalid JSON: {cleaned[:300]}") from exc
