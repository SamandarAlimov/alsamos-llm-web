"""Pollinations provider — BEPUL rasm generatsiya (API kalit talab qilmaydi).

URL formati:  https://image.pollinations.ai/prompt/<encoded-prompt>?width=..&height=..&model=..
"""
from __future__ import annotations

import urllib.parse

from .base import ImageProvider


class PollinationsProvider(ImageProvider):
    name = "pollinations"
    BASE = "https://image.pollinations.ai/prompt/"

    async def generate(self, model: str, prompt: str, width: int = 1024,
                       height: int = 1024, seed: int | None = None) -> str:
        encoded = urllib.parse.quote(prompt, safe="")
        params = {
            "width": width,
            "height": height,
            "model": model or "flux",
            "nologo": "true",
            "enhance": "true",
        }
        if seed is not None:
            params["seed"] = seed
        query = urllib.parse.urlencode(params)
        # Bevosita URL — brauzer <img> orqali yuklaydi, server-side yuklab olish shart emas.
        return f"{self.BASE}{encoded}?{query}"
