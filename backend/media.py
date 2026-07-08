"""media.py — Video / animatsiya (storyboard).

Kalitsiz "video-ga yaqin" imkoniyat: bitta promptdan bir nechta kadr (frame)
rasmini generatsiya qilib, ularni ketma-ket ko'rsatadigan storyboard/slideshow
yaratadi (frontend animatsiya bilan ijro etadi). To'liq neyro-video uchun
adapter interfeysi tayyor — kalitli provayder (masalan Runway/Pika) ulanadi.
"""
from __future__ import annotations

from typing import Dict, List

from .providers import image_provider

_BEATS = [
    "ochilish keng plani", "harakat boshlanishi", "rivojlanish", "avj nuqtasi",
    "yaqin plan (close-up)", "dramatik yorug'lik", "burilish", "tinch yakuniy kadr",
]


def scene_prompts(prompt: str, n: int = 4) -> List[str]:
    n = max(1, min(int(n), 8))
    return [f"{prompt} — {_BEATS[i % len(_BEATS)]}, cinematic, high detail"
            for i in range(n)]


async def storyboard(prompt: str, frames: int = 4, width: int = 768,
                     height: int = 432) -> Dict:
    prov = image_provider("flux")
    scenes = scene_prompts(prompt, frames)
    out: List[dict] = []
    for i, s in enumerate(scenes):
        url = await prov.generate("flux", s, width, height, seed=1000 + i)
        out.append({"index": i, "scene": s, "url": url})
    return {"prompt": prompt, "width": width, "height": height,
            "frames": out, "count": len(out),
            "note": "Storyboard/slideshow — frontend kadrlarni animatsiya bilan ijro etadi."}
