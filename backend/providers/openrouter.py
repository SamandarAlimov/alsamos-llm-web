"""OpenRouter provider — barcha bepul (:free) matn modellari uchun.

OpenAI-mos /chat/completions endpointidan foydalanadi, SSE streaming bilan.
"""
from __future__ import annotations

import json
from typing import AsyncIterator, List

from .base import TextProvider, Message, ProviderError
from .. import config


class OpenRouterProvider(TextProvider):
    name = "openrouter"

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key if api_key is not None else config.OPENROUTER_API_KEY
        self.base_url = (base_url or config.OPENROUTER_BASE_URL).rstrip("/")

    def _headers(self):
        if not self.api_key:
            raise ProviderError(
                "OPENROUTER_API_KEY topilmadi. .env faylga bepul kalitni qo'ying: "
                "https://openrouter.ai/keys"
            )
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://alsamos.com",
            "X-Title": "Alsamos LLM",
        }

    async def stream(self, model: str, messages: List[Message],
                     temperature: float = 0.7, max_tokens: int = 2048) -> AsyncIterator[str]:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        import httpx  # lazy: faqat runtime'da kerak (server ishga tushganda)
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            async with client.stream("POST", f"{self.base_url}/chat/completions",
                                     headers=self._headers(), json=payload) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", "ignore")
                    raise ProviderError(f"OpenRouter {resp.status_code}: {body[:400]}")
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        delta = obj["choices"][0]["delta"].get("content")
                        if delta:
                            yield delta
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
