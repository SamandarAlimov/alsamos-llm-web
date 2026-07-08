# Alsamos LLM — Professional AI Platform

Claude / ChatGPT / Grok / Gemini uslubidagi professional chat interfeys +
"vazifani tugatmaguncha ishlaydigan" agentic Python backend. Barcha **bepul**
modellar ulangan, haqiqiy **tool'lar** (web qidiruv, kod, Excel/CSV, geolokatsiya)
va **serverga joylab** (`ai.alsamos.com`) istalgan qurilmadan ishlatish imkoniyati.

---

## ✨ Imkoniyatlar
- **3 rejim:** 💬 Chat · 🧠 Agent · 🎨 Rasm generatsiya
- **Bepul modellar:** OpenRouter `:free` (DeepSeek R1/V3, Llama 3.3, Gemini 2.0,
  Qwen, Mistral, Gemma, Nemotron...) + Pollinations (rasm, kalitsiz).
- **Agentic yadro** (`backend/agent/`): deep reasoning → strategiya → tool-use →
  self-validation → meta-learning. Natija validatsiyadan o'tmaguncha qayta ishlaydi.
- **Haqiqiy tool'lar** (`backend/tools/`): `web_search`, `web_fetch`, `run_python`,
  `run_shell`, `spreadsheet` (Excel/CSV), `geo_lookup`, `geo_reverse`.
- **Xavfsizlik:** xavfli buyruqlar (`rm -rf /`, fork bomb, tashqi IP scan...) bloklanadi.
- **Intelligence monitor:** success rate, sifat trendi, eng samarali tool.
- **Kirish himoyasi:** ixtiyoriy parol + token (server rejimi uchun).

## 🚀 Tez start (lokal)
```bash
cd alsamos-llm
cp backend/.env.example backend/.env   # OPENROUTER_API_KEY qo'shing (matn uchun)
bash run.sh                            # → http://127.0.0.1:8000
```
> Rasm generatsiya kalitsiz ishlaydi. Matn modellari uchun bepul kalit:
> https://openrouter.ai/keys

## 🌐 Serverga joylash (ai.alsamos.com)
To'liq qo'llanma: **[DEPLOY.md](DEPLOY.md)**. Qisqacha (Docker + avtomatik HTTPS):
```bash
cp backend/.env.production.example backend/.env   # kalit + parol + secret key
docker compose up -d --build
# DNS: A-record  ai -> <SERVER_IP>
# → https://ai.alsamos.com
```

## 🔌 Integratsiya (boshqa Alsamos platformalari uchun)

Yagona zero-dependency fayl — **`alsamos_sdk.py`** — ni istalgan platformangizga
nusxalang:
```python
from alsamos_sdk import AlsamosClient
ai = AlsamosClient("https://ai.alsamos.com", api_key="sk-alsamos-...")

ai.ask("Mahsulot tavsifi yoz", system="Sen kopirayter")   # oddiy javob
ai.agent("Bozor tahlilini qidirib hisobot tayyorla")        # agentic (tool+validation)
ai.image("Toshkent, kelajak shahri")                        # bepul rasm
ai.run_python("print(2**10)")                               # tool
ai.spreadsheet(headers=["Ism","Ball"], rows=[["Ali",90]])   # Excel/CSV
```
CLI: `python alsamos_sdk.py --url https://ai.alsamos.com --key sk-... ask "Salom"`

### API kalitlar
`.env` da `ALSAMOS_API_KEYS=sk-alsamos-crm-xxx,sk-alsamos-mobile-yyy` qo'ying.
Har bir platforma o'z kalitini `X-API-Key` yoki `Authorization: Bearer <key>` da yuboradi.

### OpenAI-mos (istalgan til: JS, PHP, Go...)
Mavjud OpenAI mijozida faqat base URL ni almashtiring — kod o'zgarmaydi:
```js
import OpenAI from "openai";
const client = new OpenAI({ baseURL: "https://ai.alsamos.com/v1", apiKey: "sk-alsamos-..." });
await client.chat.completions.create({ model: "deepseek/deepseek-chat-v3-0324:free",
  messages: [{ role: "user", content: "Salom" }] });
```
Endpointlar: `POST /v1/chat/completions` (stream & non-stream), `GET /v1/models`.

## 🧪 Testlar
```bash
python3 -m backend.tests.test_agent
```
Kategoriyalar: Coding, System, Safety, Reasoning, Validation, Knowledge,
Monitor, Strategy, Tools, Auth, Orchestrator.

## 📁 Tuzilma
```
alsamos-llm/
├─ backend/
│  ├─ config.py           # modellar + sozlamalar
│  ├─ auth.py             # parol/token himoyasi
│  ├─ main.py             # FastAPI server + endpointlar
│  ├─ providers/          # OpenRouter (matn) + Pollinations (rasm)
│  ├─ agent/              # reasoning, knowledge, validation, monitor,
│  │                       #   adaptive_strategies, orchestrator
│  ├─ tools/              # safety, code_exec, web, geo, office, toolkit
│  └─ tests/
├─ frontend/              # index.html + styles.css + app.js
├─ Dockerfile, docker-compose.yml, Caddyfile, gunicorn_conf.py
├─ deploy/                # nginx.conf, systemd service
└─ DEPLOY.md, run.sh
```

## ⚙️ Asosiy .env kalitlari
| Kalit | Vazifa |
|-------|--------|
| `OPENROUTER_API_KEY` | matn modellari uchun bepul kalit |
| `ALSAMOS_PUBLIC_URL` | `https://ai.alsamos.com` |
| `ALSAMOS_ACCESS_PASSWORD` | kirish paroli (bo'sh = ochiq) |
| `ALSAMOS_SECRET_KEY` | token imzosi (`openssl rand -hex 32`) |
| `ALSAMOS_ENABLE_TOOLS` | tool'larni yoqish/o'chirish |

> `*` bilan belgilangan imkoniyatlar (video, browser boshqarish) tool-adapter
> qo'shish orqali kengaytiriladi — arxitektura shunga tayyor (`tools/toolkit.py`).

## 🖥️ TypeScript + React frontend (frontend-react/)

Asosiy interfeys endi **TypeScript + React (Vite)** bilan yozilgan va `frontend-react/` papkasida joylashgan. U barcha imkoniyatlarni qamrab oladi: **chat, agent, rasm, video** rejimlari, **artifacts** paneli (kod/HTML/SVG jonli ko'rinishi), **projects**, **skills**, **audio** (TTS eshitish + mikrofon orqali ovozli kiritish), va **framer-motion** animatsiyalari.

### Ishga tushirish (development)

```bash
cd frontend-react
npm install
npm run dev      # http://localhost:5173 (backendga :8000 proxy qiladi)
```

Backendni alohida terminalda ishga tushiring: `python -m backend.main` (yoki `bash run.sh`).

### Production build

```bash
cd frontend-react
npm install
npm run build    # natija: frontend-react/dist/
```

Backend avtomatik ravishda `frontend-react/dist/` mavjud bo'lsa **React** interfeysini, aks holda oddiy `frontend/` interfeysini xizmat qiladi. Ya'ni build qilmasangiz ham platforma ishlaydi — React build esa uni yanada kuchli qiladi.

> Eslatma: `npm install` internet talab qiladi. Server (ai.alsamos.com) deploy paytida `npm run build` ni bir marta bajaring, keyin `dist/` fayllari statik tarzda beriladi.

