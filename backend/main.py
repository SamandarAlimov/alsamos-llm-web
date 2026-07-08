"""Alsamos LLM — FastAPI server (production-ready).

Endpointlar:
  GET  /                  → frontend (chat interfeys)
  GET  /api/health        → health check (monitoring/load balancer uchun)
  GET  /api/models        → barcha bepul modellar + auth holati
  POST /api/login         → parol bilan token olish (agar himoya yoqilgan bo'lsa)
  GET  /api/metrics       → intelligence monitor ko'rsatkichlari
  GET  /api/knowledge     → o'rganilgan bilim
  POST /api/chat          → oddiy chat, SSE streaming
  POST /api/agent         → agentic rejim (tool-enabled loop), SSE
  POST /api/image         → bepul rasm generatsiya (Pollinations)
  POST /api/tools/{tool}  → tool'ni to'g'ridan chaqirish
  POST /api/safety/check  → buyruq xavfsizligini tekshirish
  GET  /files/{name}      → yaratilgan eksport fayllar (xlsx/csv)

Dev:  python -m backend.main   |   Prod: gunicorn (gunicorn_conf.py)
"""
from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, auth, projects, skills, artifacts, audio, media
from .agent import knowledge, Orchestrator, IntelligenceMonitor
from .providers import text_provider, image_provider, ProviderError
from .providers.base import Message
from .tools import safety, toolkit

app = FastAPI(title="Alsamos LLM", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

os.makedirs(config.DATA_DIR, exist_ok=True)
os.makedirs(config.EXPORTS_DIR, exist_ok=True)
_kb = knowledge.KnowledgeBase(os.path.join(config.DATA_DIR, "knowledge.json"))
_monitor = IntelligenceMonitor(os.path.join(config.DATA_DIR, "metrics.json"))

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
REACT_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend-react", "dist")

_PUBLIC_PREFIXES = ("/api/health", "/api/models", "/api/login")


def _needs_auth(path: str) -> bool:
    if path.startswith("/v1"):
        return True
    if path.startswith("/api/"):
        return not any(path.startswith(p) for p in _PUBLIC_PREFIXES)
    return False


@app.middleware("http")
async def auth_guard(request: Request, call_next):
    path = request.url.path
    if auth.protection_on() and _needs_auth(path):
        if not auth.authorize(request.headers.get("authorization"),
                              request.headers.get("x-api-key")):
            return JSONResponse({"error": "unauthorized",
                                 "message": "Kirish talab qilinadi (parol yoki API kalit)."},
                                status_code=401)
    return await call_next(request)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: Optional[str] = None
    messages: List[ChatMessage]
    temperature: float = 0.7
    project_id: Optional[str] = None
    skill_id: Optional[str] = None


class AgentRequest(BaseModel):
    model: Optional[str] = None
    task: str
    history: List[ChatMessage] = []
    use_tools: bool = True
    project_id: Optional[str] = None
    skill_id: Optional[str] = None


class ImageRequest(BaseModel):
    model: Optional[str] = None
    prompt: str
    width: int = 1024
    height: int = 1024
    seed: Optional[int] = None


class SafetyRequest(BaseModel):
    command: str


class LoginRequest(BaseModel):
    password: str


class ToolRequest(BaseModel):
    args: Dict[str, Any] = {}


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "alsamos-llm", "version": "1.0.0",
            "env": config.ENV, "models": len(config.ALL_MODELS)}


@app.post("/api/login")
def login(req: LoginRequest):
    if not auth.auth_enabled():
        return {"ok": True, "token": "", "auth": False}
    if not auth.check_password(req.password):
        return JSONResponse({"ok": False, "message": "Parol noto'g'ri."}, status_code=401)
    return {"ok": True, "token": auth.create_token(), "auth": True}


@app.get("/api/models")
def list_models():
    return {
        "text": [m.to_dict() for m in config.FREE_TEXT_MODELS],
        "image": [m.to_dict() for m in config.FREE_IMAGE_MODELS],
        "defaults": {
            "text": config.DEFAULT_TEXT_MODEL,
            "agent": config.DEFAULT_AGENT_MODEL,
            "image": config.DEFAULT_IMAGE_MODEL,
        },
        "has_key": bool(config.OPENROUTER_API_KEY),
        "auth": auth.auth_enabled(),
        "api_keys": auth.api_keys_enabled(),
        "tools": [t["name"] for t in toolkit.TOOL_SPECS] if config.ENABLE_TOOLS else [],
    }


@app.get("/api/metrics")
def metrics():
    return _monitor.metrics()


@app.get("/api/knowledge")
def knowledge_snapshot():
    return _kb.snapshot()


@app.post("/api/safety/check")
def safety_check(req: SafetyRequest):
    return safety.check_command(req.command).to_dict()


@app.post("/api/tools/{tool_name}")
async def call_tool(tool_name: str, req: ToolRequest):
    if not config.ENABLE_TOOLS:
        return JSONResponse({"ok": False, "error": "Tool'lar o'chirilgan."}, status_code=403)
    return await toolkit.dispatch(tool_name, req.args)


@app.post("/api/chat")
async def chat(req: ChatRequest):
    model = req.model or config.DEFAULT_TEXT_MODEL
    provider = text_provider(model)
    messages: List[Message] = [{"role": m.role, "content": m.content} for m in req.messages]
    extra = _extra_system(req.project_id, req.skill_id)
    if extra:
        messages = [{"role": "system", "content": extra}] + messages

    async def gen():
        try:
            async for tok in provider.stream(model, messages, temperature=req.temperature):
                yield _sse({"type": "token", "text": tok})
            yield _sse({"type": "done"})
        except ProviderError as e:
            yield _sse({"type": "error", "message": str(e)})
        except Exception as e:  # noqa
            yield _sse({"type": "error", "message": f"Kutilmagan xato: {e}"})

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/agent")
async def agent(req: AgentRequest):
    model = req.model or config.DEFAULT_AGENT_MODEL
    provider = text_provider(model)
    orch = Orchestrator(provider, _kb, _monitor, model,
                        max_iterations=config.MAX_AGENT_ITERATIONS,
                        use_tools=config.ENABLE_TOOLS and req.use_tools,
                        max_tool_calls=config.MAX_TOOL_CALLS)
    history: List[Message] = [{"role": m.role, "content": m.content} for m in req.history]
    extra_system = _extra_system(req.project_id, req.skill_id)

    async def gen():
        try:
            async for event in orch.run(req.task, history=history, extra_system=extra_system):
                yield _sse(event)
            yield _sse({"type": "done"})
        except ProviderError as e:
            yield _sse({"type": "error", "message": str(e)})
        except Exception as e:  # noqa
            yield _sse({"type": "error", "message": f"Agent xatosi: {e}"})

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/image")
async def image(req: ImageRequest):
    model = req.model or config.DEFAULT_IMAGE_MODEL
    provider = image_provider(model)
    url = await provider.generate(model, req.prompt, req.width, req.height, req.seed)
    return {"url": url, "prompt": req.prompt, "model": model}


# ===== OpenAI-mos endpointlar (boshqa platformalar oson integratsiyasi uchun) =====
# Mavjud OpenAI SDK'lari base_url ni https://ai.alsamos.com/v1 ga o'zgartirib ishlatadi.

class OAIMessage(BaseModel):
    role: str
    content: str


class OAIChatRequest(BaseModel):
    model: Optional[str] = None
    messages: List[OAIMessage]
    temperature: float = 0.7
    max_tokens: int = 2048
    stream: bool = False


@app.get("/v1/models")
def oai_models():
    return {"object": "list", "data": [
        {"id": m.id, "object": "model", "created": 0, "owned_by": f"alsamos/{m.provider}"}
        for m in config.ALL_MODELS
    ]}


@app.post("/v1/chat/completions")
async def oai_chat(req: OAIChatRequest):
    model = req.model or config.DEFAULT_TEXT_MODEL
    provider = text_provider(model)
    messages: List[Message] = [{"role": m.role, "content": m.content} for m in req.messages]
    cid = "chatcmpl-" + uuid.uuid4().hex[:24]
    created = int(time.time())

    if req.stream:
        async def gen():
            try:
                async for tok in provider.stream(model, messages,
                                                  temperature=req.temperature,
                                                  max_tokens=req.max_tokens):
                    yield _sse({"id": cid, "object": "chat.completion.chunk",
                                "created": created, "model": model,
                                "choices": [{"index": 0, "delta": {"content": tok},
                                             "finish_reason": None}]})
                yield _sse({"id": cid, "object": "chat.completion.chunk",
                            "created": created, "model": model,
                            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
                yield "data: [DONE]\n\n"
            except ProviderError as e:
                yield _sse({"error": {"message": str(e)}})
        return StreamingResponse(gen(), media_type="text/event-stream")

    try:
        text = await provider.complete(model, messages, temperature=req.temperature,
                                       max_tokens=req.max_tokens)
    except ProviderError as e:
        return JSONResponse({"error": {"message": str(e)}}, status_code=502)
    return {"id": cid, "object": "chat.completion", "created": created, "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}


# ===== Projects / Skills / Artifacts / Audio / Media (kuchaytirilgan backend) =====

def _extra_system(project_id: Optional[str], skill_id: Optional[str]) -> str:
    parts = []
    ps = projects.system_context(project_id)
    if ps:
        parts.append(ps)
    ss = skills.skill_system(skill_id)
    if ss:
        parts.append(ss)
    return "\n\n".join(parts)


class ProjectBody(BaseModel):
    name: Optional[str] = None
    instructions: Optional[str] = None
    model: Optional[str] = None
    context: Optional[List[Dict[str, Any]]] = None
    artifacts: Optional[List[str]] = None


@app.get("/api/projects")
def api_list_projects():
    return {"projects": projects.list_projects()}


@app.post("/api/projects")
def api_create_project(body: ProjectBody):
    return projects.create_project(body.name or "Yangi loyiha", body.instructions or "", body.model)


@app.get("/api/projects/{pid}")
def api_get_project(pid: str):
    p = projects.get_project(pid)
    if not p:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return p


@app.put("/api/projects/{pid}")
def api_update_project(pid: str, body: ProjectBody):
    p = projects.update_project(pid, **body.dict(exclude_unset=True))
    if not p:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return p


@app.delete("/api/projects/{pid}")
def api_delete_project(pid: str):
    return {"deleted": projects.delete_project(pid)}


class SkillBody(BaseModel):
    name: str
    description: str = ""
    system: str = ""
    tools: List[str] = []
    icon: str = "\u2728"


@app.get("/api/skills")
def api_list_skills():
    return {"skills": skills.list_skills()}


@app.post("/api/skills")
def api_create_skill(body: SkillBody):
    return skills.create_skill(body.name, body.description, body.system, body.tools, body.icon)


@app.delete("/api/skills/{sid}")
def api_delete_skill(sid: str):
    return {"deleted": skills.delete_skill(sid)}


class ArtifactBody(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    content: Optional[str] = None
    language: Optional[str] = None
    project_id: Optional[str] = None


@app.get("/api/artifacts")
def api_list_artifacts(project_id: Optional[str] = None):
    return {"artifacts": artifacts.list_artifacts(project_id)}


@app.post("/api/artifacts")
def api_create_artifact(body: ArtifactBody):
    return artifacts.create_artifact(body.title or "Artefakt", body.type or "code",
                                     body.content or "", body.language, body.project_id)


@app.get("/api/artifacts/{aid}")
def api_get_artifact(aid: str):
    a = artifacts.get_artifact(aid)
    if not a:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return a


@app.put("/api/artifacts/{aid}")
def api_update_artifact(aid: str, body: ArtifactBody):
    a = artifacts.update_artifact(aid, content=body.content, title=body.title, language=body.language)
    if not a:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return a


@app.delete("/api/artifacts/{aid}")
def api_delete_artifact(aid: str):
    return {"deleted": artifacts.delete_artifact(aid)}


class TTSBody(BaseModel):
    text: str
    voice: str = audio.DEFAULT_VOICE


@app.get("/api/audio/voices")
def api_voices():
    return {"voices": audio.VOICES, "default": audio.DEFAULT_VOICE}


@app.post("/api/audio/tts")
def api_tts(body: TTSBody):
    return {"url": audio.tts_url(body.text, body.voice), "voice": body.voice}


class MediaBody(BaseModel):
    prompt: str
    frames: int = 4
    width: int = 768
    height: int = 432


@app.post("/api/media/storyboard")
async def api_storyboard(body: MediaBody):
    return await media.storyboard(body.prompt, body.frames, body.width, body.height)


if os.path.isdir(config.EXPORTS_DIR):
    app.mount("/files", StaticFiles(directory=config.EXPORTS_DIR), name="files")

# React (Vite) build ustunlik oladi; bo'lmasa eski frontend'ga qaytadi.
_SPA_DIR = REACT_DIST if os.path.isdir(REACT_DIST) else (
    FRONTEND_DIR if os.path.isdir(FRONTEND_DIR) else None)

if _SPA_DIR:
    _assets_dir = os.path.join(_SPA_DIR, "assets")
    if os.path.isdir(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")
    app.mount("/static", StaticFiles(directory=_SPA_DIR), name="static")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(_SPA_DIR, "index.html"))

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        candidate = os.path.join(_SPA_DIR, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(_SPA_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    print(f"\n  Alsamos LLM  →  http://{config.HOST}:{config.PORT}\n")
    uvicorn.run(app, host=config.HOST, port=config.PORT)
