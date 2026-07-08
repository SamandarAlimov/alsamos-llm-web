"""projects.py — Loyihalar (ChatGPT/Claude "Projects" uslubi).

Har bir loyiha: nomi, ko'rsatmalar (system context), model, kontekst fayllar,
va bog'langan artefaktlar. Suhbatlar loyiha ko'rsatmalarini avtomatik oladi.
"""
from __future__ import annotations

import os
from typing import List, Optional

from . import config
from .store import JsonStore, new_id, now

_store = JsonStore(os.path.join(config.DATA_DIR, "projects.json"))


def list_projects() -> List[dict]:
    return sorted(_store.all(), key=lambda p: p.get("updated", 0), reverse=True)


def get_project(pid: str) -> Optional[dict]:
    return _store.get(pid)


def create_project(name: str, instructions: str = "", model: Optional[str] = None) -> dict:
    p = {
        "id": new_id("proj"),
        "name": name or "Yangi loyiha",
        "instructions": instructions or "",
        "model": model,
        "context": [],       # [{title, content}]
        "artifacts": [],      # artifact id lar
        "created": now(),
        "updated": now(),
    }
    return _store.put(p)


def update_project(pid: str, **fields) -> Optional[dict]:
    p = _store.get(pid)
    if not p:
        return None
    for k in ("name", "instructions", "model", "context", "artifacts"):
        if k in fields and fields[k] is not None:
            p[k] = fields[k]
    p["updated"] = now()
    return _store.put(p)


def delete_project(pid: str) -> bool:
    return _store.delete(pid)


def system_context(pid: Optional[str]) -> str:
    """Loyiha ko'rsatmalari + kontekstini system prompt matniga aylantiradi."""
    if not pid:
        return ""
    p = _store.get(pid)
    if not p:
        return ""
    parts = []
    if p.get("instructions"):
        parts.append(f"# LOYIHA: {p['name']}\n{p['instructions']}")
    for c in p.get("context", []):
        if c.get("content"):
            parts.append(f"## Kontekst: {c.get('title','')}\n{c['content']}")
    return "\n\n".join(parts)
