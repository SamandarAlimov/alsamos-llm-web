"""Alsamos LLM — configuration and free-model catalog.

Barcha sozlamalar bu yerda. API kalitlarni `.env` faylga qo'ying.
Production uchun .env.production.example ga qarang.
"""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field, asdict
from typing import List

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # dotenv ixtiyoriy
    pass


def _bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on", "ha")


# --- Provayder / modellar ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_BASE_URL = os.getenv(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
).rstrip("/")

# --- Server ---
HOST = os.getenv("ALSAMOS_HOST", "127.0.0.1")
PORT = int(os.getenv("ALSAMOS_PORT", "8000"))
PUBLIC_URL = os.getenv("ALSAMOS_PUBLIC_URL", "").rstrip("/")  # masalan https://ai.alsamos.com
ENV = os.getenv("ALSAMOS_ENV", "development")  # development | production
_origins = os.getenv("ALSAMOS_ALLOWED_ORIGINS", "*").strip()
ALLOWED_ORIGINS = ["*"] if _origins in ("", "*") else [o.strip() for o in _origins.split(",") if o.strip()]

# --- Xotira / eksport ---
_BASE = os.path.dirname(__file__)
DATA_DIR = os.getenv("ALSAMOS_DATA_DIR", os.path.join(_BASE, ".alsamos_state"))
EXPORTS_DIR = os.getenv("ALSAMOS_EXPORTS_DIR", os.path.join(DATA_DIR, "exports"))

# --- Agent ---
MAX_AGENT_ITERATIONS = int(os.getenv("ALSAMOS_MAX_ITERS", "6"))
MAX_TOOL_CALLS = int(os.getenv("ALSAMOS_MAX_TOOL_CALLS", "4"))
ENABLE_TOOLS = _bool("ALSAMOS_ENABLE_TOOLS", True)
ALLOW_EXTERNAL_NET = _bool("ALSAMOS_ALLOW_EXTERNAL_NET", True)  # web/geo tool'lar uchun

# --- Xavfsizlik / kirish ---
# Bo'sh bo'lsa — ochiq (auth yo'q). To'ldirilsa — kirish parol bilan himoyalanadi.
ACCESS_PASSWORD = os.getenv("ALSAMOS_ACCESS_PASSWORD", "").strip()
SECRET_KEY = os.getenv("ALSAMOS_SECRET_KEY", "").strip() or secrets.token_hex(32)
TOKEN_TTL_SECONDS = int(os.getenv("ALSAMOS_TOKEN_TTL", str(60 * 60 * 24 * 30)))  # 30 kun

# --- Integratsiya: machine-to-machine API kalitlari ---
# Boshqa Alsamos platformalari X-API-Key yoki `Authorization: Bearer <key>`
# orqali kiradi. Vergul bilan bir nechta kalit qo'yish mumkin.
_api_keys = os.getenv("ALSAMOS_API_KEYS", "").strip()
API_KEYS: List[str] = [k.strip() for k in _api_keys.split(",") if k.strip()]


@dataclass
class ModelInfo:
    id: str
    name: str
    provider: str          # "openrouter" | "pollinations"
    kind: str              # "text" | "image"
    context: int = 8192
    description: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


FREE_TEXT_MODELS: List[ModelInfo] = [
    ModelInfo("deepseek/deepseek-r1:free", "DeepSeek R1", "openrouter", "text",
              65536, "Kuchli reasoning modeli — Alsamos agent uchun tavsiya etiladi.",
              ["reasoning", "tavsiya"]),
    ModelInfo("deepseek/deepseek-chat-v3-0324:free", "DeepSeek V3", "openrouter", "text",
              65536, "Tez, umumiy maqsadli chat modeli.", ["chat", "general"]),
    ModelInfo("meta-llama/llama-3.3-70b-instruct:free", "Llama 3.3 70B", "openrouter", "text",
              131072, "Meta ochiq modeli, kuchli umumiy imkoniyatlar.", ["general"]),
    ModelInfo("meta-llama/llama-3.2-11b-vision-instruct:free", "Llama 3.2 Vision", "openrouter", "text",
              131072, "Rasmni ko'radi (vision) + matn.", ["vision", "multimodal"]),
    ModelInfo("google/gemini-2.0-flash-exp:free", "Gemini 2.0 Flash", "openrouter", "text",
              1048576, "Google, juda katta kontekst, tez.", ["long-context", "fast"]),
    ModelInfo("google/gemma-3-27b-it:free", "Gemma 3 27B", "openrouter", "text",
              131072, "Google ochiq modeli.", ["general"]),
    ModelInfo("qwen/qwen-2.5-72b-instruct:free", "Qwen 2.5 72B", "openrouter", "text",
              32768, "Alibaba, kod va matematikada kuchli.", ["code", "math"]),
    ModelInfo("qwen/qwq-32b:free", "Qwen QwQ 32B", "openrouter", "text",
              32768, "Reasoning-ga ixtisoslashgan.", ["reasoning"]),
    ModelInfo("mistralai/mistral-small-3.1-24b-instruct:free", "Mistral Small 3.1", "openrouter", "text",
              32768, "Yengil, tez, ishonchli.", ["fast"]),
    ModelInfo("mistralai/mistral-nemo:free", "Mistral Nemo", "openrouter", "text",
              131072, "Kompakt va samarali.", ["fast"]),
    ModelInfo("nvidia/llama-3.1-nemotron-70b-instruct:free", "Nemotron 70B", "openrouter", "text",
              131072, "NVIDIA fine-tuned Llama.", ["general"]),
]

FREE_IMAGE_MODELS: List[ModelInfo] = [
    ModelInfo("flux", "FLUX (Pollinations)", "pollinations", "image",
              0, "Yuqori sifatli bepul rasm generatsiya, kalit talab qilmaydi.",
              ["image", "free"]),
    ModelInfo("flux-realism", "FLUX Realism", "pollinations", "image",
              0, "Fotorealistik uslub.", ["image", "realism"]),
    ModelInfo("turbo", "Turbo", "pollinations", "image",
              0, "Eng tez rasm generatsiya.", ["image", "fast"]),
]

ALL_MODELS = FREE_TEXT_MODELS + FREE_IMAGE_MODELS
DEFAULT_TEXT_MODEL = "deepseek/deepseek-chat-v3-0324:free"
DEFAULT_AGENT_MODEL = "deepseek/deepseek-r1:free"
DEFAULT_IMAGE_MODEL = "flux"


def get_model(model_id: str) -> ModelInfo | None:
    for m in ALL_MODELS:
        if m.id == model_id:
            return m
    return None
