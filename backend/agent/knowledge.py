"""knowledge.py — Knowledge building & meta-learning.

Har muvaffaqiyatli task'dan texnika o'rganadi va domain bo'yicha expertise
darajasini oshiradi: novice → beginner → competent → proficient → expert.
Disk'da JSON sifatida saqlanadi (uzoq muddatli xotira).
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List

LEVELS = ["novice", "beginner", "competent", "proficient", "expert"]
# Har daraja uchun kerakli muvaffaqiyatli task soni.
_THRESHOLDS = [0, 3, 8, 18, 40]


@dataclass
class DomainKnowledge:
    domain: str
    successes: int = 0
    failures: int = 0
    techniques: List[str] = field(default_factory=list)
    lessons: List[str] = field(default_factory=list)

    @property
    def level(self) -> str:
        lvl = "novice"
        for i, thr in enumerate(_THRESHOLDS):
            if self.successes >= thr:
                lvl = LEVELS[i]
        return lvl

    def to_dict(self):
        d = asdict(self)
        d["level"] = self.level
        return d


class KnowledgeBase:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        self.domains: Dict[str, DomainKnowledge] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                for name, d in raw.items():
                    self.domains[name] = DomainKnowledge(
                        domain=name,
                        successes=d.get("successes", 0),
                        failures=d.get("failures", 0),
                        techniques=d.get("techniques", []),
                        lessons=d.get("lessons", []),
                    )
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({k: v.to_dict() for k, v in self.domains.items()}, f,
                      ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def _get(self, domain: str) -> DomainKnowledge:
        if domain not in self.domains:
            self.domains[domain] = DomainKnowledge(domain=domain)
        return self.domains[domain]

    def learn(self, domain: str, success: bool, technique: str | None = None,
              lesson: str | None = None):
        """Task natijasidan o'rganadi."""
        with self._lock:
            dk = self._get(domain)
            if success:
                dk.successes += 1
                if technique and technique not in dk.techniques:
                    dk.techniques.append(technique)
            else:
                dk.failures += 1
                # Meta-learning: xatodan metodologiya darsini oladi.
                if lesson and lesson not in dk.lessons:
                    dk.lessons.append(lesson)
            self._save()
            return dk.to_dict()

    def recall(self, domain: str) -> Dict:
        with self._lock:
            dk = self._get(domain)
            return dk.to_dict()

    def context_for(self, domain: str, limit: int = 5) -> str:
        """LLM prompt'iga qo'shiladigan o'rganilgan bilim konteksti."""
        dk = self._get(domain)
        if not dk.techniques and not dk.lessons:
            return ""
        lines = [f"# LEARNED KNOWLEDGE ({domain} — daraja: {dk.level})"]
        if dk.techniques:
            lines.append("Ishlagan texnikalar:")
            lines += [f"- {t}" for t in dk.techniques[-limit:]]
        if dk.lessons:
            lines.append("O'tmish xatolaridan saboqlar:")
            lines += [f"- {l}" for l in dk.lessons[-limit:]]
        return "\n".join(lines)

    def snapshot(self) -> Dict:
        with self._lock:
            return {k: v.to_dict() for k, v in self.domains.items()}


def classify_domain(task: str) -> str:
    """Task matnidan domenni aniqlaydi."""
    t = task.lower()
    table = [
        (("code", "kod", "python", "function", "api", "bug", "debug"), "coding"),
        (("rasm", "image", "design", "logo", "video"), "creative"),
        (("data", "csv", "json", "sql", "analiz", "analyze"), "data"),
        (("yoz", "write", "maqola", "matn", "blog", "essay"), "writing"),
        (("reja", "plan", "strategy", "strategiya", "arxitektura"), "planning"),
    ]
    for keys, domain in table:
        if any(k in t for k in keys):
            return domain
    return "general"
