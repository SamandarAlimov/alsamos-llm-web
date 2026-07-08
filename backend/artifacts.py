"""artifacts.py — Artefaktlar (Claude/ChatGPT "Artifacts" uslubi).

Artefakt = alohida panelda ko'rsatiladigan va tahrirlanadigan natija:
kod, HTML, markdown, SVG, mermaid diagramma yoki React komponent.
Versiyalar saqlanadi (har yangilanishda oldingi versiya tarixga qo'shiladi).
"""
from __future__ import annotations

import os
from typing import List, Optional

from . import config
from .store import JsonStore, new_id, now

_store = JsonStore(os.path.join(config.DATA_DIR, "artifacts.json"))

TYPES = ["code", "html", "markdown", "svg", "mermaid", "react"]


def list_artifacts(project_id: Optional[str] = None) -> List[dict]:
    items = sorted(_store.all(), key=lambda a: a.get("updated", 0), reverse=True)
    if project_id:
        items = [a for a in items if a.get("project_id") == project_id]
    return items


def get_artifact(aid: str) -> Optional[dict]:
    return _store.get(aid)


def create_artifact(title: str, type: str, content: str,
                    language: Optional[str] = None,
                    project_id: Optional[str] = None) -> dict:
    a = {"id": new_id("art"), "title": title or "Artefakt",
         "type": type if type in TYPES else "code",
         "language": language or "", "content": content or "",
         "project_id": project_id, "versions": [],
         "created": now(), "updated": now()}
    return _store.put(a)


def update_artifact(aid: str, content: Optional[str] = None,
                    title: Optional[str] = None,
                    language: Optional[str] = None) -> Optional[dict]:
    a = _store.get(aid)
    if not a:
        return None
    if content is not None and content != a.get("content"):
        a.setdefault("versions", []).append({"content": a.get("content", ""), "ts": a.get("updated", now())})
        a["content"] = content
    if title is not None:
        a["title"] = title
    if language is not None:
        a["language"] = language
    a["updated"] = now()
    return _store.put(a)


def delete_artifact(aid: str) -> bool:
    return _store.delete(aid)
