"""toolkit.py — agent uchun yagona tool registri va dispatcher.

Agent modeliga tool'lardan foydalanish imkonini beradi (ReAct uslubi):
model bitta qatorda `TOOL_CALL {"name":..,"args":{..}}` chiqaradi, biz uni
bajaramiz va natijani qaytaramiz. Har bir tool API orqali ham chaqiriladi.
"""
from __future__ import annotations

import json
from typing import Any, Dict

from . import web, geo, office, code_exec, safety
from .. import config

TOOL_SPECS = [
    {"name": "web_search", "args": {"query": "str"},
     "desc": "Internetdan qidirish (kalit shart emas). Dolzarb ma'lumot uchun."},
    {"name": "web_fetch", "args": {"url": "str"},
     "desc": "Berilgan URL sahifasi matnini o'qish."},
    {"name": "run_python", "args": {"code": "str"},
     "desc": "Python kodini xavfsiz sandbox'da ishga tushirish, natijani olish."},
    {"name": "run_shell", "args": {"command": "str"},
     "desc": "Shell buyrug'ini ishga tushirish (xavfli buyruqlar bloklanadi)."},
    {"name": "spreadsheet", "args": {"headers": "list", "rows": "list[list]", "filename": "str?", "format": "xlsx|csv?"},
     "desc": "Excel/CSV jadval yaratish va yuklab olinadigan havola qaytarish."},
    {"name": "geo_lookup", "args": {"ip": "str?"},
     "desc": "IP bo'yicha geolokatsiya (bo'sh bo'lsa server joylashuvi)."},
    {"name": "geo_reverse", "args": {"lat": "float", "lon": "float"},
     "desc": "Koordinatadan manzil aniqlash."},
]


def specs_prompt() -> str:
    lines = ["# MAVJUD TOOL'LAR",
             "Agar tashqi ma'lumot, hisoblash, kod ishga tushirish yoki fayl kerak bo'lsa,",
             "AYNAN bitta qatorda quyidagicha yoz (boshqa hech narsa yozma):",
             'TOOL_CALL {"name":"<tool>","args":{...}}',
             "Tool natijasi berilgach, davom et. Tool kerak bo'lmasa — to'g'ridan yakuniy javob ber.",
             "", "Tool'lar:"]
    for t in TOOL_SPECS:
        lines.append(f"- {t['name']}({', '.join(t['args'].keys())}) — {t['desc']}")
    return "\n".join(lines)


async def dispatch(name: str, args: Dict[str, Any]) -> Dict:
    args = args or {}
    try:
        if name == "web_search":
            if not config.ALLOW_EXTERNAL_NET:
                return {"ok": False, "error": "Tashqi tarmoq o'chirilgan."}
            return {"ok": True, "result": await web.search(str(args.get("query", "")))}
        if name == "web_fetch":
            if not config.ALLOW_EXTERNAL_NET:
                return {"ok": False, "error": "Tashqi tarmoq o'chirilgan."}
            return {"ok": True, "result": await web.fetch(str(args.get("url", "")))}
        if name == "run_python":
            res = code_exec.run_python(str(args.get("code", "")))
            return {"ok": res.ok, "result": res.to_dict()}
        if name == "run_shell":
            res = code_exec.run_shell(str(args.get("command", "")))
            return {"ok": res.ok, "result": res.to_dict()}
        if name == "spreadsheet":
            info = office.build_spreadsheet(
                rows=args.get("rows", []), headers=args.get("headers"),
                fmt=args.get("format", "xlsx"), filename=args.get("filename"),
                out_dir=config.EXPORTS_DIR)
            base = config.PUBLIC_URL or ""
            info["download_url"] = f"{base}/files/{info['filename']}"
            return {"ok": True, "result": info}
        if name == "geo_lookup":
            if not config.ALLOW_EXTERNAL_NET:
                return {"ok": False, "error": "Tashqi tarmoq o'chirilgan."}
            return {"ok": True, "result": await geo.lookup(args.get("ip"))}
        if name == "geo_reverse":
            if not config.ALLOW_EXTERNAL_NET:
                return {"ok": False, "error": "Tashqi tarmoq o'chirilgan."}
            return {"ok": True, "result": await geo.reverse(float(args["lat"]), float(args["lon"]))}
        return {"ok": False, "error": f"Noma'lum tool: {name}"}
    except Exception as e:  # noqa
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def extract_tool_call(text: str):
    """Matndan TOOL_CALL {json} ni ajratadi. (name, args) yoki None."""
    if "TOOL_CALL" not in text:
        return None
    idx = text.find("TOOL_CALL")
    rest = text[idx + len("TOOL_CALL"):].strip()
    brace = rest.find("{")
    if brace == -1:
        return None
    depth = 0
    end = -1
    for i, ch in enumerate(rest[brace:], start=brace):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end == -1:
        return None
    try:
        obj = json.loads(rest[brace:end])
    except json.JSONDecodeError:
        return None
    name = obj.get("name")
    if not name:
        return None
    return name, obj.get("args", {}) or {}
