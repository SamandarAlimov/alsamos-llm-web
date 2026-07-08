"""reasoning.py — Deep reasoning engine.

Har bir task'ni ANALYTICAL + CREATIVE ikki nuqtai nazardan tahlil qiladi,
risk / assumption / dependency topadi. Murakkab tasklarda 4 bosqichli
"deep reasoning" rejimini yoqadi.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import List

# Murakkablikni oshiruvchi belgilar (heuristik).
# Diqqat: prefiks mosligi uchun oxirgi \b qo'yilmagan (masalan "arxitekturasini").
_COMPLEX_HINTS = re.compile(
    r"\b(?:arxitektura|architecture|design|distribut|scal|optimi|refactor|"
    r"debug|integrat|migrat|security|xavfsiz|algorithm|algoritm|reason|"
    r"strateg|perform|multi[- ]?step|ko'p bosqich|analyze|analiz|tahlil|"
    r"plan|rejalash)",
    re.IGNORECASE,
)


@dataclass
class ReasoningResult:
    task: str
    complexity: str                    # "simple" | "moderate" | "complex"
    deep_reasoning: bool
    analytical: List[str] = field(default_factory=list)
    creative: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    stages: List[str] = field(default_factory=list)   # 4 bosqichli fikrlash

    def to_dict(self):
        return asdict(self)


def _score_complexity(task: str) -> str:
    length = len(task.split())
    hint_hits = len(_COMPLEX_HINTS.findall(task))
    score = hint_hits * 2 + (length // 40)
    if score >= 4 or length > 120:
        return "complex"
    if score >= 2 or length > 40:
        return "moderate"
    return "simple"


def analyze(task: str) -> ReasoningResult:
    """Task'ni tahlil qiladi va reasoning rejasini qaytaradi."""
    complexity = _score_complexity(task)
    deep = complexity == "complex"

    analytical = [
        "Task'ning aniq talablari va muvaffaqiyat mezonlari nima?",
        "Kirish/chiqish (input/output) shakli qanday bo'lishi kerak?",
        "Qaysi cheklovlar (performance, xavfsizlik, resurs) mavjud?",
    ]
    creative = [
        "Muammoni hal qilishning kamida 2 muqobil yo'li bormi?",
        "Ushbu yechimni qanday qilib soddaroq yoki chiroyliroq qilish mumkin?",
        "Kutilmagan qirralar (edge case)larni oldindan qanday qamrab olamiz?",
    ]
    risks = [
        "Noto'liq yoki noaniq talab tufayli xato yechim.",
        "Tashqi bog'liqlik (API, tarmoq) ishlamay qolishi.",
    ]
    assumptions = [
        "Foydalanuvchi kiritmalari asosan to'g'ri formatda keladi.",
        "Kerakli resurslar (kalit, ruxsat) mavjud.",
    ]
    dependencies = _extract_dependencies(task)

    stages: List[str] = []
    if deep:
        stages = [
            "1. DECOMPOSE — muammoni mustaqil kichik bo'laklarga ajratish.",
            "2. EXPLORE — har bo'lak uchun yechim variantlarini ko'rib chiqish.",
            "3. SYNTHESIZE — eng yaxshi variantlarni yagona yechimga birlashtirish.",
            "4. CRITIQUE — yechimni tanqidiy qayta ko'rib, zaif joylarni tuzatish.",
        ]

    return ReasoningResult(
        task=task, complexity=complexity, deep_reasoning=deep,
        analytical=analytical, creative=creative, risks=risks,
        assumptions=assumptions, dependencies=dependencies, stages=stages,
    )


def _extract_dependencies(task: str) -> List[str]:
    deps = []
    checks = {
        r"\b(api|endpoint|http|request)\b": "Tashqi API / tarmoq ulanishi",
        r"\b(fayl|file|csv|json|read|write|yozish|o'qish)\b": "Fayl tizimi kirishi",
        r"\b(db|database|sql|postgres|redis|mongo)\b": "Ma'lumotlar bazasi",
        r"\b(rasm|image|video|media)\b": "Media generatsiya/qayta ishlash",
    }
    for pat, label in checks.items():
        if re.search(pat, task, re.IGNORECASE):
            deps.append(label)
    return deps


def build_reasoning_prompt(r: ReasoningResult) -> str:
    """LLM uchun reasoning konteksti (system-message qismi sifatida)."""
    lines = [
        "# INTERNAL REASONING PLAN",
        f"Murakkablik: {r.complexity} | Deep reasoning: {r.deep_reasoning}",
        "",
        "Analytical savollar:",
        *[f"- {x}" for x in r.analytical],
        "Creative savollar:",
        *[f"- {x}" for x in r.creative],
        "Risklar:",
        *[f"- {x}" for x in r.risks],
        "Taxminlar:",
        *[f"- {x}" for x in r.assumptions],
    ]
    if r.dependencies:
        lines += ["Bog'liqliklar:", *[f"- {x}" for x in r.dependencies]]
    if r.stages:
        lines += ["", "4 bosqichli chuqur fikrlash:", *r.stages]
    return "\n".join(lines)
