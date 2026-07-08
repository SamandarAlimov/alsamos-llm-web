"""orchestrator.py — Alsamos agentic engine (tool-enabled).

"Vazifani tugatmaguncha to'xtamaydigan" yadro. Oqim (pipeline):

  reasoning → strategy → (execute → [tool-use]* → self-validate → adapt)* → knowledge + metrics

Agent kerak bo'lganda TOOL_CALL orqali haqiqiy tool'lardan foydalanadi
(web qidiruv, kod ishga tushirish, jadval, geolokatsiya...). Har iteratsiyada
natijani validatsiya qiladi; o'tmasa — o'zini tuzatib qayta urinadi.
Bu "savolga javob" emas, YAKUNLANGAN natija beradi.
"""
from __future__ import annotations

import json
import time
from typing import AsyncIterator, Dict, List, Optional

from . import reasoning, knowledge, validation, adaptive_strategies
from .intelligence_monitor import IntelligenceMonitor, TaskRecord
from ..providers.base import TextProvider, Message


SYSTEM_IDENTITY = (
    "Sen — Alsamos LLM, professional darajada MULOHAZA yuritadigan va REAL "
    "YAKUNIY NATIJA yetkazadigan agentsan. Faqat savolga javob berish emas, "
    "balki vazifani to'liq bajarish sening maqsading. Aniq, ishlaydigan, "
    "to'liq va xavfsiz yechim ber. Kod so'ralganda — to'liq, ishga tushadigan "
    "kod yoz. O'zbek tilida so'ralsa o'zbekcha javob ber."
)


class Orchestrator:
    def __init__(self, provider: TextProvider, kb: knowledge.KnowledgeBase,
                 monitor: IntelligenceMonitor, model: str,
                 max_iterations: int = 6, use_tools: bool = True,
                 max_tool_calls: int = 4):
        self.provider = provider
        self.kb = kb
        self.monitor = monitor
        self.model = model
        self.max_iterations = max_iterations
        self.use_tools = use_tools
        self.max_tool_calls = max_tool_calls

    async def run(self, task: str, history: Optional[List[Message]] = None,
                  extra_system: Optional[str] = None) -> AsyncIterator[Dict]:
        history = history or []
        started = time.time()
        domain = knowledge.classify_domain(task)
        tools_used: List[str] = ["reasoning", "strategy", "validation", "monitor"]

        # 1) REASONING
        yield {"type": "stage", "stage": "reasoning",
               "label": "🧠 Deep reasoning — kontekst tahlil qilinmoqda"}
        r = reasoning.analyze(task)
        yield {"type": "reasoning", "data": r.to_dict()}

        # 2) STRATEGY
        yield {"type": "stage", "stage": "strategy",
               "label": "🎯 Strategiya tanlanmoqda"}
        strat = adaptive_strategies.select(task, r.complexity, domain)
        max_iters = min(self.max_iterations, strat.max_iterations)
        yield {"type": "strategy", "data": strat.to_dict()}

        val_level = validation.level_for_complexity(r.complexity)
        learned = self.kb.context_for(domain)

        system_parts = [SYSTEM_IDENTITY]
        if extra_system:
            system_parts.append(extra_system)
        system_parts += [reasoning.build_reasoning_prompt(r),
                         f"# STRATEGY: {strat.name}\n{strat.rationale}"]
        if learned:
            system_parts.append(learned)
        if self.use_tools:
            try:
                from ..tools import toolkit
                system_parts.append(toolkit.specs_prompt())
            except Exception:
                pass
        system_prompt = "\n\n".join(system_parts)

        # 3) ITERATIVE EXECUTION + TOOL USE + SELF-VALIDATION
        messages: List[Message] = [{"role": "system", "content": system_prompt}]
        messages += history
        messages.append({"role": "user", "content": task})

        best_output = ""
        best_report = None
        success = False
        attempts = 0
        tool_calls = 0

        while attempts < max_iters:
            step_no = attempts + 1
            yield {"type": "iteration", "n": step_no, "of": max_iters,
                   "label": f"⚙️ Bajarilmoqda — urinish {step_no}/{max_iters}"}

            chunks: List[str] = []
            try:
                async for tok in self.provider.stream(
                        self.model, messages, temperature=0.5, max_tokens=3072):
                    chunks.append(tok)
                    yield {"type": "token", "text": tok, "iteration": step_no}
            except Exception as e:
                yield {"type": "error", "message": str(e)}
                break
            output = "".join(chunks).strip()

            # --- TOOL USE ---
            tc = None
            if self.use_tools and tool_calls < self.max_tool_calls:
                try:
                    from ..tools import toolkit
                    tc = toolkit.extract_tool_call(output)
                except Exception:
                    tc = None
            if tc is not None:
                name, args = tc
                tool_calls += 1
                if name not in tools_used:
                    tools_used.append(name)
                yield {"type": "tool", "phase": "call", "name": name, "args": args}
                from ..tools import toolkit
                result = await toolkit.dispatch(name, args)
                yield {"type": "tool", "phase": "result", "name": name,
                       "ok": result.get("ok", False), "data": result}
                messages.append({"role": "assistant", "content": output})
                messages.append({"role": "user", "content":
                    "TOOL_RESULT " + json.dumps(result, ensure_ascii=False)[:3500]
                    + "\nEndi natijadan foydalanib davom et yoki yakuniy javobni ber."})
                continue  # tool bosqichi — urinish sifatida sanalmaydi

            # --- VALIDATION ---
            attempts += 1
            best_output = output or best_output
            report = validation.validate(output, task=task, level=val_level)
            best_report = report
            yield {"type": "validation", "iteration": attempts, "data": report.to_dict()}

            if report.passed:
                success = True
                break

            critique = report.critique()
            yield {"type": "stage", "stage": "adapt",
                   "label": "🔄 Kamchiliklar topildi — yechim yaxshilanmoqda"}
            messages.append({"role": "assistant", "content": output})
            messages.append({"role": "user", "content":
                "Quyidagi self-review natijasi bo'yicha yechimni TUZAT va TO'LIQ "
                "yakuniy versiyani qaytar (faqat farqni emas):\n" + critique})

        # 4) KNOWLEDGE + META-LEARNING
        quality = best_report.score if best_report else 0.0
        if success:
            self.kb.learn(domain, True, technique=f"{strat.name} ({val_level})")
        else:
            lesson = (best_report.critique() if best_report else
                      "Validation o'tmadi — talab aniqroq bo'lishi kerak.")
            self.kb.learn(domain, False, lesson=lesson[:200])

        # 5) INTELLIGENCE MONITORING
        duration = round(time.time() - started, 2)
        self.monitor.record(TaskRecord(
            task=task[:160], domain=domain, success=success,
            duration_s=duration, quality=quality, iterations=max(attempts, 1),
            tools_used=tools_used,
        ))

        yield {"type": "final", "success": success, "output": best_output,
               "quality": quality, "iterations": max(attempts, 1),
               "tool_calls": tool_calls, "domain": domain, "duration_s": duration,
               "knowledge": self.kb.recall(domain)}
        yield {"type": "metrics", "data": self.monitor.metrics()}
