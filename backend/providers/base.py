"""Provider abstraksiyasi — barcha model provayderlari shu interfeysga amal qiladi."""
from __future__ import annotations

from typing import AsyncIterator, Dict, List

Message = Dict[str, str]  # {"role": "user"|"assistant"|"system", "content": "..."}


class ProviderError(RuntimeError):
    pass


class TextProvider:
    """Matn modellari uchun bazaviy provider."""

    name = "base"

    async def stream(self, model: str, messages: List[Message],
                     temperature: float = 0.7, max_tokens: int = 2048) -> AsyncIterator[str]:
        raise NotImplementedError
        yield  # pragma: no cover

    async def complete(self, model: str, messages: List[Message],
                       temperature: float = 0.7, max_tokens: int = 2048) -> str:
        """Stream'ni to'liq matnga yig'adi (agent ichki chaqiruvlari uchun)."""
        parts: List[str] = []
        async for chunk in self.stream(model, messages, temperature, max_tokens):
            parts.append(chunk)
        return "".join(parts)


class ImageProvider:
    """Rasm generatsiya provideri."""

    name = "base-image"

    async def generate(self, model: str, prompt: str, width: int = 1024,
                       height: int = 1024, seed: int | None = None) -> str:
        """Rasm URL yoki data-uri qaytaradi."""
        raise NotImplementedError
