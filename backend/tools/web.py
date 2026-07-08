"""web.py — haqiqiy web qidiruv va sahifa o'qish (keyless).

- search(): DuckDuckGo Instant Answer API (kalit talab qilmaydi).
- fetch(): URL matnini yuklab, HTML teglarini tozalaydi.
Tashqi tarmoq kerak; ALSAMOS_ALLOW_EXTERNAL_NET bilan boshqariladi.
"""
from __future__ import annotations

import re
from typing import Dict, List

_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_WS_RE = re.compile(r"[ \t\r\f\v]+")
_NL_RE = re.compile(r"\n{3,}")


async def search(query: str, max_results: int = 5) -> Dict:
    import httpx
    url = "https://api.duckduckgo.com/"
    params = {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"}
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as c:
        r = await c.get(url, params=params, headers={"User-Agent": "AlsamosLLM/1.0"})
        data = r.json()
    results: List[Dict] = []
    if data.get("AbstractText"):
        results.append({"title": data.get("Heading", query),
                        "snippet": data["AbstractText"],
                        "url": data.get("AbstractURL", "")})
    for topic in data.get("RelatedTopics", []):
        if len(results) >= max_results:
            break
        if isinstance(topic, dict) and topic.get("Text"):
            results.append({"title": topic.get("Text", "")[:80],
                            "snippet": topic.get("Text", ""),
                            "url": topic.get("FirstURL", "")})
    return {"query": query, "results": results[:max_results],
            "answer": data.get("Answer") or data.get("AbstractText", "")}


async def fetch(url: str, max_chars: int = 4000) -> Dict:
    import httpx
    async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as c:
        r = await c.get(url, headers={"User-Agent": "AlsamosLLM/1.0"})
        html = r.text
    text = _SCRIPT_RE.sub(" ", html)
    text = _TAG_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text)
    text = _NL_RE.sub("\n\n", text)
    text = text.strip()
    truncated = len(text) > max_chars
    return {"url": url, "text": text[:max_chars], "truncated": truncated,
            "length": len(text)}
