"""audio.py — Ovoz (TTS). Kalitsiz matndan-nutqqa.

- tts_url(text, voice): StreamElements keyless TTS — mp3 havolasini qaytaradi.
- STT (nutqdan-matnga) frontendda brauzerning Web Speech API'si orqali bajariladi
  (server kerak emas), shuning uchun bu yerda faqat TTS bor.
"""
from __future__ import annotations

import urllib.parse
from typing import List

# StreamElements (Amazon Polly ovozlari) — kalit talab qilmaydi.
VOICES: List[str] = ["Brian", "Amy", "Emma", "Joey", "Justin", "Salli",
                     "Nicole", "Russell", "Matthew", "Ivy"]
DEFAULT_VOICE = "Brian"


def tts_url(text: str, voice: str = DEFAULT_VOICE) -> str:
    v = voice if voice in VOICES else DEFAULT_VOICE
    t = (text or "").strip()[:1000]
    return ("https://api.streamelements.com/kappa/v2/speech?voice="
            + urllib.parse.quote(v) + "&text=" + urllib.parse.quote(t))
