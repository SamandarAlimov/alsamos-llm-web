"""geo.py — geolokatsiya (keyless).

- lookup(ip): IP bo'yicha joylashuv (ipapi.co).
- reverse(lat, lon): koordinatadan manzil (OpenStreetMap Nominatim).
Tashqi tarmoq kerak.
"""
from __future__ import annotations

from typing import Dict, Optional


async def lookup(ip: Optional[str] = None) -> Dict:
    import httpx
    if ip:
        url = "https://ipapi.co/" + str(ip) + "/json/"
    else:
        url = "https://ipapi.co/json/"
    async with httpx.AsyncClient(timeout=20.0) as c:
        r = await c.get(url, headers={"User-Agent": "AlsamosLLM/1.0"})
        d = r.json()
    return {"ip": d.get("ip"), "city": d.get("city"), "region": d.get("region"),
            "country": d.get("country_name"), "lat": d.get("latitude"),
            "lon": d.get("longitude"), "org": d.get("org"),
            "timezone": d.get("timezone")}


async def reverse(lat: float, lon: float) -> Dict:
    import httpx
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"lat": lat, "lon": lon, "format": "json"}
    async with httpx.AsyncClient(timeout=20.0) as c:
        r = await c.get(url, params=params,
                        headers={"User-Agent": "AlsamosLLM/1.0 (contact@alsamos.com)"})
        d = r.json()
    return {"lat": lat, "lon": lon, "address": d.get("display_name"),
            "details": d.get("address", {})}
