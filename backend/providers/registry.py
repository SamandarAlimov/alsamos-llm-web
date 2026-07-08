"""Provider registry — model_id bo'yicha to'g'ri provayderni tanlaydi."""
from __future__ import annotations

from .openrouter import OpenRouterProvider
from .pollinations import PollinationsProvider
from .base import TextProvider, ImageProvider
from .. import config

_openrouter = OpenRouterProvider()
_pollinations = PollinationsProvider()


def text_provider(model_id: str) -> TextProvider:
    info = config.get_model(model_id)
    if info and info.provider == "openrouter":
        return _openrouter
    # Default: OpenRouter (barcha bepul matn modellari shu yerda)
    return _openrouter


def image_provider(model_id: str) -> ImageProvider:
    return _pollinations


def default_text_provider() -> TextProvider:
    return _openrouter
