"""
Alsamos LLM SDK — bitta faylli integratsiya klienti (zero-dependency).
================================================================

Alsamos Corporation'ning boshqa platformalariga (CRM, mobil backend, ERP, bot...)
shu YAGONA faylni nusxalab qo'ying va ishlating. Faqat Python standart
kutubxonasi (urllib) ishlatiladi — hech qanday qo'shimcha paket kerak emas.
Python 3.8+.

--- Tez boshlash ---
    from alsamos_sdk import AlsamosClient

    ai = AlsamosClient("https://ai.alsamos.com", api_key="sk-alsamos-...")

    # 1) Oddiy savol-javob
    print(ai.ask("Mahsulot tavsifini yozib ber", system="Sen marketing kopirayterisan"))

    # 2) Streaming (real vaqt)
    for tok in ai.chat_stream([{"role":"user","content":"Salom"}]):
        print(tok, end="")

    # 3) Agentic rejim (reasoning + tool + validation, yakuniy natija)
    res = ai.agent("Oxirgi AI yangiliklarini qidirib, qisqa hisobot tayyorla")
    print(res["output"], res["success"], res["iterations"])

    # 4) Bepul rasm
    url = ai.image("Toshkent, kelajak shahri, neon")

    # 5) Tool'ni to'g'ridan chaqirish
    ai.run_python("print(2**10)")
    ai.spreadsheet(headers=["Ism","Ball"], rows=[["Ali",90],["Vali",85]], format="xlsx")

--- OpenAI-mos rejim (mavjud kutubxonalar bilan) ---
    Har qanday tilda (JS/PHP/Go...) mavjud OpenAI mijozida faqat base URL ni
    almashtiring:  https://ai.alsamos.com/v1   (api_key = Alsamos API kaliti)
    Masalan Python `openai` paketi:
        from openai import OpenAI
        client = OpenAI(base_url="https://ai.alsamos.com/v1", api_key="sk-alsamos-...")
        client.chat.completions.create(model="deepseek/deepseek-chat-v3-0324:free",
                                       messages=[{"role":"user","content":"Salom"}])

--- CLI ---
    python alsamos_sdk.py --url https://ai.alsamos.com --key sk-... ask "Salom"
    python alsamos_sdk.py --url https://ai.alsamos.com --key sk-... agent "FizzBuzz yoz"
    python alsamos_sdk.py --url https://ai.alsamos.com --key sk-... image "tog' manzarasi"
"""
from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any, Callable, Dict, Iterator, List, Optional

__version__ = "1.0.0"
__all__ = ["AlsamosClient", "AlsamosError"]

Message = Dict[str, str]


class AlsamosError(RuntimeError):
    """Alsamos API xatosi."""


class AlsamosClient:
    """Alsamos LLM platformasi bilan integratsiya uchun qulay klient.

    Parametrlar:
        base_url: masalan "https://ai.alsamos.com"
        api_key : machine-to-machine kirish uchun API kalit (tavsiya etiladi)
        password: yoki foydalanuvchi paroli (token olinadi)
        timeout : soniyalarda (agent uchun uzunroq bo'lsin)
        default_model: standart model id (ixtiyoriy)
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None,
                 password: Optional[str] = None, timeout: float = 180.0,
                 default_model: Optional[str] = None):
        if not base_url:
            raise ValueError("base_url majburiy (masalan https://ai.alsamos.com)")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.password = password
        self.timeout = timeout
        self.default_model = default_model
        self._token: Optional[str] = None
        if password and not api_key:
            self.login(password)

    # ---------- ichki ----------
    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json", "Accept": "application/json",
             "User-Agent": f"alsamos-sdk/{__version__}"}
        if self.api_key:
            h["X-API-Key"] = self.api_key
            h["Authorization"] = "Bearer " + self.api_key
        elif self._token:
            h["Authorization"] = "Bearer " + self._token
        return h

    def _open(self, method: str, path: str, body: Optional[dict] = None):
        url = self.base_url + path
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers=self._headers())
        try:
            return urllib.request.urlopen(req, timeout=self.timeout)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")
            if e.code == 401:
                raise AlsamosError("Avtorizatsiya xatosi (401): API kalit yoki parolni tekshiring.") from None
            raise AlsamosError(f"HTTP {e.code}: {detail}") from None
        except urllib.error.URLError as e:
            raise AlsamosError(f"Ulanish xatosi: {e.reason}") from None

    def _json(self, method: str, path: str, body: Optional[dict] = None) -> dict:
        resp = self._open(method, path, body)
        raw = resp.read().decode("utf-8", "ignore")
        return json.loads(raw) if raw else {}

    def _sse(self, method: str, path: str, body: Optional[dict] = None) -> Iterator[dict]:
        resp = self._open(method, path, body)
        buf = ""
        for raw in resp:
            buf += raw.decode("utf-8", "ignore")
            while "\n\n" in buf:
                block, buf = buf.split("\n\n", 1)
                for line in block.splitlines():
                    if line.startswith("data:"):
                        payload = line[5:].strip()
                        if payload == "[DONE]":
                            return
                        try:
                            yield json.loads(payload)
                        except json.JSONDecodeError:
                            pass

    # ---------- avtorizatsiya ----------
    def login(self, password: Optional[str] = None) -> Optional[str]:
        """Parol bilan token oladi (agar platformada parol yoqilgan bo'lsa)."""
        res = self._json("POST", "/api/login", {"password": password or self.password or ""})
        if not res.get("ok"):
            raise AlsamosError("Login muvaffaqiyatsiz: parol noto'g'ri.")
        self._token = res.get("token") or None
        return self._token

    # ---------- holat ----------
    def health(self) -> dict:
        return self._json("GET", "/api/health")

    def models(self) -> dict:
        return self._json("GET", "/api/models")

    def metrics(self) -> dict:
        return self._json("GET", "/api/metrics")

    def knowledge(self) -> dict:
        return self._json("GET", "/api/knowledge")

    # ---------- chat ----------
    def chat_stream(self, messages: List[Message], model: Optional[str] = None,
                    temperature: float = 0.7) -> Iterator[str]:
        body = {"model": model or self.default_model, "messages": messages,
                "temperature": temperature}
        for ev in self._sse("POST", "/api/chat", body):
            t = ev.get("type")
            if t == "token":
                yield ev.get("text", "")
            elif t == "error":
                raise AlsamosError(ev.get("message", "chat xatosi"))

    def chat(self, messages: List[Message], model: Optional[str] = None,
             temperature: float = 0.7) -> str:
        return "".join(self.chat_stream(messages, model, temperature))

    def ask(self, prompt: str, system: Optional[str] = None,
            model: Optional[str] = None, temperature: float = 0.7) -> str:
        msgs: List[Message] = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        return self.chat(msgs, model, temperature)

    # ---------- agent ----------
    def agent_stream(self, task: str, model: Optional[str] = None,
                     history: Optional[List[Message]] = None,
                     use_tools: bool = True) -> Iterator[dict]:
        body = {"task": task, "model": model or self.default_model,
                "history": history or [], "use_tools": use_tools}
        for ev in self._sse("POST", "/api/agent", body):
            yield ev

    def agent(self, task: str, model: Optional[str] = None,
              history: Optional[List[Message]] = None, use_tools: bool = True,
              on_event: Optional[Callable[[dict], None]] = None) -> dict:
        """Agentic rejim. Yakuniy natija dict qaytaradi:
        {output, success, quality, iterations, tool_calls, domain, duration_s, knowledge}.
        """
        final: dict = {}
        for ev in self.agent_stream(task, model, history, use_tools):
            if on_event:
                on_event(ev)
            if ev.get("type") == "final":
                final = ev
            elif ev.get("type") == "error":
                raise AlsamosError(ev.get("message", "agent xatosi"))
        return final

    # ---------- rasm ----------
    def image(self, prompt: str, model: Optional[str] = None, width: int = 1024,
              height: int = 1024, seed: Optional[int] = None) -> str:
        body = {"prompt": prompt, "model": model, "width": width,
                "height": height, "seed": seed}
        return self._json("POST", "/api/image", body).get("url", "")

    # ---------- tool'lar ----------
    def run_tool(self, name: str, **args: Any) -> dict:
        return self._json("POST", "/api/tools/" + name, {"args": args})

    def web_search(self, query: str) -> dict:
        return self.run_tool("web_search", query=query)

    def web_fetch(self, url: str) -> dict:
        return self.run_tool("web_fetch", url=url)

    def run_python(self, code: str) -> dict:
        return self.run_tool("run_python", code=code)

    def spreadsheet(self, headers: List[str], rows: List[list],
                    filename: Optional[str] = None, format: str = "xlsx") -> dict:
        return self.run_tool("spreadsheet", headers=headers, rows=rows,
                             filename=filename, format=format)

    def geo_lookup(self, ip: Optional[str] = None) -> dict:
        return self.run_tool("geo_lookup", ip=ip)

    # ---------- OpenAI-mos ----------
    def openai_chat(self, messages: List[Message], model: Optional[str] = None,
                    temperature: float = 0.7, max_tokens: int = 2048) -> dict:
        """Standart OpenAI chat.completion formatida javob qaytaradi."""
        body = {"model": model or self.default_model or "deepseek/deepseek-chat-v3-0324:free",
                "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        return self._json("POST", "/v1/chat/completions", body)


# ================= CLI =================
def _cli(argv: List[str]) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Alsamos LLM SDK CLI")
    p.add_argument("--url", default="http://127.0.0.1:8000", help="platforma manzili")
    p.add_argument("--key", default=None, help="API kalit")
    p.add_argument("--password", default=None, help="parol (kalit o'rniga)")
    p.add_argument("--model", default=None)
    p.add_argument("cmd", choices=["ask", "agent", "image", "health", "models"])
    p.add_argument("text", nargs="*")
    a = p.parse_args(argv)
    c = AlsamosClient(a.url, api_key=a.key, password=a.password, default_model=a.model)
    text = " ".join(a.text)
    try:
        if a.cmd == "ask":
            for tok in c.chat_stream([{"role": "user", "content": text}]):
                print(tok, end="", flush=True)
            print()
        elif a.cmd == "agent":
            def _ev(e: dict):
                t = e.get("type")
                if t == "stage":
                    print("::", e.get("label"))
                elif t == "tool":
                    print(">> tool", e.get("name"), e.get("phase"))
            r = c.agent(text, on_event=_ev)
            print("\n=== NATIJA ===\n" + r.get("output", ""))
        elif a.cmd == "image":
            print(c.image(text))
        elif a.cmd == "health":
            print(json.dumps(c.health(), indent=2, ensure_ascii=False))
        elif a.cmd == "models":
            print(json.dumps(c.models(), indent=2, ensure_ascii=False))
    except AlsamosError as e:
        print("XATO:", e)
        return 1
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_cli(sys.argv[1:]))
