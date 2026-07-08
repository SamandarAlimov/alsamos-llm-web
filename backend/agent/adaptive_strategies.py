"""adaptive_strategies.py — Strategy adaptation.

Task turi bo'yicha strategiya tanlaydi:
  divide-and-conquer — murakkab, bo'linadigan masalalar
  iterative          — aniqlik/sifat asta-sekin oshadigan masalalar
  heuristic          — oddiy, tez yechiladigan masalalar
va har biri uchun BATAFSIL tushuntirish yozadi.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List


@dataclass
class Strategy:
    name: str
    rationale: str
    steps: List[str] = field(default_factory=list)
    max_iterations: int = 3

    def to_dict(self):
        return asdict(self)


def select(task: str, complexity: str, domain: str) -> Strategy:
    """reasoning natijasi asosida strategiya tanlaydi."""
    if complexity == "complex":
        return Strategy(
            name="divide-and-conquer",
            rationale=(
                "Task murakkab va bir nechta mustaqil qismga ega. Uni kichik, "
                "alohida hal qilinadigan bo'laklarga ajratamiz, har birini yakka "
                "holda yechamiz, so'ng natijalarni yagona ishonchli yechimga "
                "birlashtiramiz. Bu murakkablikni kamaytiradi va xatolarni "
                "lokalizatsiya qiladi."
            ),
            steps=[
                "Masalani mustaqil kichik vazifalarga ajrating.",
                "Har bir vazifani alohida yeching va tekshiring.",
                "Qismlarni integratsiya qiling va chegaralarni sinang.",
                "Yakuniy yechimni yaxlit qayta ko'rib chiqing.",
            ],
            max_iterations=5,
        )
    if complexity == "moderate" or domain in ("writing", "creative", "data"):
        return Strategy(
            name="iterative",
            rationale=(
                "Yechim sifati bosqichma-bosqich oshiriladi. Avval ishlaydigan "
                "qoralama (draft) yaratamiz, so'ng self-validation orqali "
                "kamchiliklarni topib, har iteratsiyada yaxshilaymiz — talab "
                "qondirilguncha."
            ),
            steps=[
                "Birinchi ishlaydigan versiyani yarating.",
                "Validation orqali kamchiliklarni aniqlang.",
                "Feedback asosida yaxshilang va qayta baholang.",
            ],
            max_iterations=4,
        )
    return Strategy(
        name="heuristic",
        rationale=(
            "Task oddiy va aniq. Ortiqcha rejalashtirishsiz, tajribaga asoslangan "
            "to'g'ridan-to'g'ri yechimni beramiz va bir marta tekshiramiz."
        ),
        steps=[
            "To'g'ridan-to'g'ri yechimni bering.",
            "Bir marta tez tekshiruv o'tkazing.",
        ],
        max_iterations=2,
    )
