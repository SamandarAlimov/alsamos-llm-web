"""store.py — oddiy, fayl asosidagi JSON do'kon (projects/skills/artifacts uchun).

Kichik, bog'liqliksiz, thread-xavfsiz (jarayon ichida) kalit-qiymat do'koni.
Har bir yozuv "id" maydoniga ega dict.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from typing import Dict, List, Optional

_locks: Dict[str, threading.Lock] = {}


def _lock(path: str) -> threading.Lock:
    return _locks.setdefault(path, threading.Lock())


class JsonStore:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def _read(self) -> Dict[str, dict]:
        try:
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _write(self, data: Dict[str, dict]) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def all(self) -> List[dict]:
        with _lock(self.path):
            return list(self._read().values())

    def get(self, item_id: str) -> Optional[dict]:
        with _lock(self.path):
            return self._read().get(item_id)

    def put(self, item: dict) -> dict:
        with _lock(self.path):
            d = self._read()
            d[item["id"]] = item
            self._write(d)
            return item

    def delete(self, item_id: str) -> bool:
        with _lock(self.path):
            d = self._read()
            existed = d.pop(item_id, None) is not None
            self._write(d)
            return existed


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def now() -> int:
    return int(time.time())
