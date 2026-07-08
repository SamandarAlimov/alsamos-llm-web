# Alsamos LLM — Serverga joylash (ai.alsamos.com)

Bu qo'llanma platformani serverga joylab, **ai.alsamos.com** orqali istalgan
qurilmadan (telefon, noutbuk, planshet) kirib ishlatish uchun.

---

## 0. Talablar
- Public IP'ga ega Linux server (Ubuntu 22.04+ tavsiya). Masalan sizning Oracle Cloud ARM instansiyangiz.
- `alsamos.com` domeni sizda bor.
- Bepul OpenRouter kaliti: https://openrouter.ai/keys

## 1. DNS — subdomenni serverga yo'naltirish
Domen boshqaruv panelida (yoki Cloudflare) **A-record** qo'shing:

| Type | Name | Value |
|------|------|-------|
| A | `ai` | `<SERVER_IP>` |

> Cloudflare ishlatsangiz: dastlab **DNS only** (kulrang bulut) qilib TLS'ni Caddy oldirsin,
> yoki “Full (strict)” rejimida proxy yoqilsa ham bo'ladi.

`ai.alsamos.com` → server IP ga yo'naltirilganini tekshiring: `ping ai.alsamos.com`

---

## 2. Usul A — Docker + Caddy (TAVSIYA, avtomatik HTTPS)

```bash
# serverda
git clone <repo> alsamos-llm   # yoki ZIP ni ko'chirib oching
cd alsamos-llm

cp backend/.env.production.example backend/.env
nano backend/.env         # kalit, parol, secret key ni to'ldiring
```

`backend/.env` da muhim qatorlar:
```
OPENROUTER_API_KEY=sk-or-...
ALSAMOS_PUBLIC_URL=https://ai.alsamos.com
ALSAMOS_ALLOWED_ORIGINS=https://ai.alsamos.com
ALSAMOS_ACCESS_PASSWORD=<kuchli-parol>
ALSAMOS_SECRET_KEY=<openssl rand -hex 32 natijasi>
```

`Caddyfile` da domen to'g'ri turibdi (`ai.alsamos.com`). Endi ishga tushiring:
```bash
docker compose up -d --build
```

Caddy avtomatik Let's Encrypt sertifikatini oladi. Tayyor:
**https://ai.alsamos.com** 🎉

Loglar / boshqaruv:
```bash
docker compose logs -f
docker compose restart
docker compose down
```

---

## 3. Usul B — Docker'siz (systemd + Nginx + Certbot)

```bash
sudo mkdir -p /opt/alsamos-llm && cd /opt/alsamos-llm
# fayllarni shu yerga joylang
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.production.example backend/.env && nano backend/.env
```

systemd service:
```bash
sudo cp deploy/alsamos-llm.service /etc/systemd/system/alsamos-llm.service
sudo systemctl daemon-reload
sudo systemctl enable --now alsamos-llm
```

Nginx + HTTPS:
```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/ai.alsamos.com
sudo ln -s /etc/nginx/sites-available/ai.alsamos.com /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d ai.alsamos.com   # bepul TLS
```

---

## 4. Xavfsizlik (professional sozlash)
- **ALSAMOS_ACCESS_PASSWORD** ni albatta to'ldiring — shunda platforma parol bilan himoyalanadi
  va faqat siz kira olasiz (token 30 kun saqlanadi, `localStorage`da).
- **ALSAMOS_SECRET_KEY** — `openssl rand -hex 32` bilan yarating, sir saqlang.
- Server o'chib-yonganda ham holat saqlanadi (Docker volume `alsamos_state` / `.alsamos_state`).
- Faqat 80/443 portlarni oching; 8000 to'g'ridan ochilmasin (reverse proxy orqasida).

## 5. Yangilash
```bash
# Docker
git pull && docker compose up -d --build
# systemd
git pull && source .venv/bin/activate && pip install -r backend/requirements.txt && sudo systemctl restart alsamos-llm
```

## 6. Tez tekshiruv
```bash
curl https://ai.alsamos.com/api/health
# {"status":"ok",...}
```

Muammo bo'lsa: DNS yetib borganini, 80/443 ochiqligini, `.env` to'g'riligini va
`docker compose logs -f` loglarini tekshiring.
