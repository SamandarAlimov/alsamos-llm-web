"""validation.py — Self-validation engine.

O'z ishini 4 darajada tekshiradi:
  basic      → correctness (asosiy to'g'rilik)
  thorough   → + completeness (to'liqlik)
  rigorous   → + security (xavfsizlik)
  exhaustive → + performance (samaradorlik)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict

LEVELS = ["basic", "thorough", "rigorous", "exhaustive"]
_DIMENSIONS = {
    "basic": ["correctness"],
    "thorough": ["correctness", "completeness"],
    "rigorous": ["correctness", "completeness", "security"],
    "exhaustive": ["correctness", "completeness", "security", "performance"],
}

_INSECURE = re.compile(
    r"(eval\(|exec\(|os\.system|subprocess\.(call|run|Popen)\(|pickle\.loads|"
    r"password\s*=\s*[\"'][^\"']+[\"']|api[_-]?key\s*=\s*[\"'][^\"']+[\"']|"
    r"rm\s+-rf\s+/)",
    re.IGNORECASE,
)


@dataclass
class Issue:
    dimension: str
    severity: str   # "info" | "warning" | "error"
    message: str

    def to_dict(self):
        return asdict(self)


@dataclass
class ValidationReport:
    level: str
    passed: bool
    score: float                       # 0..1
    issues: List[Issue] = field(default_factory=list)
    checked: List[str] = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        return d

    def critique(self) -> str:
        if self.passed and not self.issues:
            return "Validation o'tdi — muammo topilmadi."
        lines = [f"Validation ({self.level}) natijasi — ball: {self.score:.2f}"]
        for i in self.issues:
            lines.append(f"[{i.severity.upper()}] {i.dimension}: {i.message}")
        return "\n".join(lines)


def validate(output: str, task: str = "", level: str = "thorough",
             expected_markers: List[str] | None = None) -> ValidationReport:
    if level not in _DIMENSIONS:
        level = "thorough"
    dims = _DIMENSIONS[level]
    issues: List[Issue] = []

    # correctness
    if not output or not output.strip():
        issues.append(Issue("correctness", "error", "Chiqish bo'sh."))
    if expected_markers:
        for m in expected_markers:
            if m.lower() not in output.lower():
                issues.append(Issue("correctness", "warning",
                                    f"Kutilgan element topilmadi: '{m}'."))

    # completeness
    if "completeness" in dims:
        if re.search(r"(TODO|FIXME|\.\.\.|to be implemented|keyinroq)", output, re.IGNORECASE):
            issues.append(Issue("completeness", "warning",
                                "Yakunlanmagan qism (TODO/...) mavjud."))
        if len(output.strip()) < 20 and len(task.split()) > 5:
            issues.append(Issue("completeness", "warning",
                                "Javob task murakkabligiga nisbatan juda qisqa."))

    # security
    if "security" in dims:
        for match in _INSECURE.findall(output):
            issues.append(Issue("security", "error",
                                f"Xavfli/nozik pattern aniqlandi: {match!r}."))

    # performance
    if "performance" in dims:
        if re.search(r"for .+ in .+:\s*\n\s*for .+ in .+:\s*\n\s*for ", output):
            issues.append(Issue("performance", "warning",
                                "3 qavatli ichma-ich sikl — O(n^3), optimallashtiring."))

    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    score = max(0.0, 1.0 - 0.34 * len(errors) - 0.12 * len(warnings))
    passed = len(errors) == 0 and score >= 0.6
    return ValidationReport(level=level, passed=passed, score=round(score, 2),
                            issues=issues, checked=dims)


def level_for_complexity(complexity: str) -> str:
    return {
        "simple": "basic",
        "moderate": "thorough",
        "complex": "rigorous",
    }.get(complexity, "thorough")
