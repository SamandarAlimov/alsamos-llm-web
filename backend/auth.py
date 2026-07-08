"""auth.py — ixtiyoriy parol bilan kirish himoyasi (stateless HMAC token).

- ALSAMOS_ACCESS_PASSWORD bo'sh bo'lsa — auth o'chirilgan (ochiq).
- To'ldirilsa — /api/login orqali token olinadi, himoyalangan endpointlar
  Authorization: Bearer <token> talab qiladi.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from . import config


def auth_enabled() -> bool:
    return bool(config.ACCESS_PASSWORD)


def _sign(msg: bytes) -> str:
    return hmac.new(config.SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()


def check_password(password: str) -> bool:
    if not auth_enabled():
        return True
    return hmac.compare_digest(password or "", config.ACCESS_PASSWORD)


def create_token(ttl: int | None = None) -> str:
    exp = int(time.time()) + (ttl if ttl is not None else config.TOKEN_TTL_SECONDS)
    payload = json.dumps({"exp": exp}, separators=(",", ":")).encode()
    b = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    return f"{b}.{_sign(b.encode())}"


def verify_token(token: str) -> bool:
    if not auth_enabled():
        return True
    if not token:
        return False
    try:
        b, sig = token.split(".", 1)
    except ValueError:
        return False
    if not hmac.compare_digest(sig, _sign(b.encode())):
        return False
    try:
        pad = "=" * (-len(b) % 4)
        payload = json.loads(base64.urlsafe_b64decode(b + pad))
    except (ValueError, json.JSONDecodeError):
        return False
    return int(payload.get("exp", 0)) > int(time.time())


def bearer_from_header(header: str | None) -> str:
    if not header:
        return ""
    parts = header.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return header.strip()


# ===== Integratsiya: API-kalit avtorizatsiyasi (machine-to-machine) =====

def api_keys_enabled() -> bool:
    return bool(config.API_KEYS)


def protection_on() -> bool:
    """Parol yoki API kalit yoqilgan bo'lsa — himoya faol."""
    return auth_enabled() or api_keys_enabled()


def verify_api_key(key: str) -> bool:
    if not key:
        return False
    for k in config.API_KEYS:
        if hmac.compare_digest(key, k):
            return True
    return False


def authorize(auth_header: str | None, api_key_header: str | None) -> bool:
    """So'rovni avtorizatsiya qiladi: API kalit (X-API-Key/Bearer) yoki user token."""
    if not protection_on():
        return True
    if api_keys_enabled():
        if verify_api_key((api_key_header or "").strip()):
            return True
        b = bearer_from_header(auth_header)
        if b and verify_api_key(b):
            return True
    if auth_enabled():
        if verify_token(bearer_from_header(auth_header)):
            return True
    return False
