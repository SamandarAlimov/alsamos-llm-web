"""intelligence_monitor.py — Performance monitoring.

Doimiy o'lchaydi: success rate, o'rtacha tezlik, quality trend,
qaysi tool eng samarali. Disk'da JSON sifatida saqlanadi.
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Dict, List


@dataclass
class TaskRecord:
    task: str
    domain: str
    success: bool
    duration_s: float
    quality: float          # validation ball 0..1
    iterations: int
    tools_used: List[str] = field(default_factory=list)
    ts: float = field(default_factory=time.time)

    def to_dict(self):
        return asdict(self)


class IntelligenceMonitor:
    def __init__(self, path: str, window: int = 200):
        self.path = path
        self.window = window
        self._lock = threading.Lock()
        self.records: List[TaskRecord] = []
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                self.records = [TaskRecord(**r) for r in raw][-self.window:]
            except (json.JSONDecodeError, OSError, TypeError):
                pass

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in self.records[-self.window:]], f,
                      ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def record(self, rec: TaskRecord):
        with self._lock:
            self.records.append(rec)
            self.records = self.records[-self.window:]
            self._save()

    def metrics(self) -> Dict:
        with self._lock:
            recs = list(self.records)
        if not recs:
            return {"total": 0, "success_rate": 0.0, "avg_duration_s": 0.0,
                    "avg_quality": 0.0, "quality_trend": "n/a",
                    "best_tool": None, "avg_iterations": 0.0}
        total = len(recs)
        succ = sum(1 for r in recs if r.success)
        avg_dur = sum(r.duration_s for r in recs) / total
        avg_q = sum(r.quality for r in recs) / total
        avg_it = sum(r.iterations for r in recs) / total

        # Quality trend: oxirgi 25% vs birinchi 25%.
        trend = "stable"
        if total >= 8:
            k = max(2, total // 4)
            early = sum(r.quality for r in recs[:k]) / k
            late = sum(r.quality for r in recs[-k:]) / k
            if late - early > 0.05:
                trend = "improving"
            elif early - late > 0.05:
                trend = "declining"

        # Eng samarali tool (muvaffaqiyatli tasklarda eng ko'p ishlatilgan).
        tool_success = defaultdict(lambda: [0, 0])  # tool -> [succ, total]
        for r in recs:
            for t in r.tools_used:
                tool_success[t][1] += 1
                if r.success:
                    tool_success[t][0] += 1
        best_tool = None
        best_rate = -1.0
        for tool, (s, tot) in tool_success.items():
            rate = s / tot if tot else 0
            if tot >= 2 and rate > best_rate:
                best_rate, best_tool = rate, tool

        return {
            "total": total,
            "success_rate": round(succ / total, 3),
            "avg_duration_s": round(avg_dur, 2),
            "avg_quality": round(avg_q, 3),
            "avg_iterations": round(avg_it, 2),
            "quality_trend": trend,
            "best_tool": best_tool,
        }
