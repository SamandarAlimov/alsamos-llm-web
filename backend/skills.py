"""skills.py — Ko'nikmalar (Claude "Skills" uslubi).

Skill = qayta ishlatiladigan mutaxassislik: maxsus system prompt + tavsiya
etilgan tool'lar. Foydalanuvchi skill tanlaydi, u chat/agent so'roviga qo'shiladi.
O'rnatilgan (builtin) sk"illar + foydalanuvchi qo'shgan (custom) skillar.
"""
from __future__ import annotations

import os
from typing import List, Optional

from . import config
from .store import JsonStore, new_id, now

_store = JsonStore(os.path.join(config.DATA_DIR, "skills.json"))

BUILTIN: List[dict] = [
    {"id": "skill_code_review", "name": "Kod tahlili", "icon": "\U0001F50D", "builtin": True,
     "description": "Kodni xatolar, xavfsizlik va uslub bo'yicha chuqur tekshiradi.",
     "system": "Sen tajribali senior code reviewer'san. Kodni tahlil qil: xatolar, "
               "xavfsizlik zaifliklari, performance va uslub. Aniq tuzatishlar va "
               "yaxshilangan kod versiyasini ber.",
     "tools": ["run_python"]},
    {"id": "skill_data_analyst", "name": "Data tahlilchi", "icon": "\U0001F4CA", "builtin": True,
     "description": "Ma'lumotni tahlil qiladi, hisoblaydi va jadval/hisobot tayyorlaydi.",
     "system": "Sen data-analitiksan. Ma'lumotni tahlil qil, statistik xulosa chiqar, "
               "kerak bo'lsa Python bilan hisobla va natijani jadval (spreadsheet) qilib ber.",
     "tools": ["run_python", "spreadsheet"]},
    {"id": "skill_researcher", "name": "Tadqiqotchi", "icon": "\U0001F9EA", "builtin": True,
     "description": "Internetdan qidiradi, manbalarni o'qiydi va asosli xulosa beradi.",
     "system": "Sen tadqiqotchisan. Internetdan dolzarb ma'lumot qidir (web_search/web_fetch), "
               "manbalarni solishtir va manbali, asosli xulosa yoz.",
     "tools": ["web_search", "web_fetch"]},
    {"id": "skill_writer", "name": "Kopirayter", "icon": "\u270D\uFE0F", "builtin": True,
     "description": "Professional, jozibali matn yozadi (marketing, blog, ssenariy).",
     "system": "Sen professional kopirayter va muharrirsan. Aniq auditoriya uchun "
               "jozibali, tuzilgan va uslubi to'g'ri matn yoz.",
     "tools": []},
    {"id": "skill_designer", "name": "UI dizayner", "icon": "\U0001F3A8", "builtin": True,
     "description": "HTML/CSS/React komponent va dizayn tizimini yaratadi (artifact).",
     "system": "Sen mahsulot dizayneri va frontend muhandisisisan. Zamonaviy, chiroyli "
               "HTML/CSS yoki React komponent yarat. Kodni to'liq, ishga tushadigan qilib ber "
               "(artifact sifatida ko'rsatiladi).",
     "tools": []},
    {"id": "skill_translator_uz", "name": "Tarjimon (UZ)", "icon": "\U0001F310", "builtin": True,
     "description": "Matnni tabiiy o'zbek tiliga yoki o'zbekchadan tarjima qiladi.",
     "system": "Sen professional tarjimonsan. Matnni tabiiy, ravon o'zbek tiliga (yoki "
               "so'ralgan tilga) tarjima qil, ma'no va uslubni saqla.",
     "tools": []},
]


def list_skills() -> List[dict]:
    return BUILTIN + _store.all()


def get_skill(sid: str) -> Optional[dict]:
    for s in BUILTIN:
        if s["id"] == sid:
            return s
    return _store.get(sid)


def create_skill(name: str, description: str, system: str,
                 tools: Optional[List[str]] = None, icon: str = "\u2728") -> dict:
    s = {"id": new_id("skill"), "name": name, "description": description or "",
         "system": system or "", "tools": tools or [], "icon": icon,
         "builtin": False, "created": now()}
    return _store.put(s)


def delete_skill(sid: str) -> bool:
    if any(s["id"] == sid for s in BUILTIN):
        return False  # builtin o'chirilmaydi
    return _store.delete(sid)


def skill_system(sid: Optional[str]) -> str:
    if not sid:
        return ""
    s = get_skill(sid)
    if not s:
        return ""
    return f"# SKILL: {s['name']}\n{s.get('system','')}"
