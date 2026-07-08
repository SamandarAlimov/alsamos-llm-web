# 🚀 Alsamos AI — Oracle Cloud'ga joylashtirish (to'liq qo'llanma)

Bu qo'llanma butun platformani (React frontend + Python backend + agent) **bitta Oracle Cloud serverida**, `ai.alsamos.com` domenida, avtomatik HTTPS bilan ishga tushiradi.

> Arxitektura: `ai.alsamos.com → Caddy (avtomatik SSL) → FastAPI (React'ni ham o'zi beradi)`. Hammasi Docker ichida. Vercel kerak emas.

---

## 0. Nima kerak
- Oracle Cloud instansiyasi (siz allaqachon ochgansiz ✅). Tavsiya: **Ubuntu 22.04**, shakl **Ampere A1 (ARM)** yoki AMD — Always Free ham yetarli.
- Domen: `alsamos.com` (DNS boshqaruvi bilan).
- Bepul OpenRouter API kaliti: https://openrouter.ai/keys

---

## 1. Kodni GitHub'ga yuklash (lokal kompyuteringizda)
Arxivni oching, `alsamos-llm/` papkasiga kiring va:
```bash
git init
git add .
git commit -m "Alsamos AI platform"
git branch -M main
git remote add origin https://github.com/SamandarAlimov/alsamos-llm-web.git
git push -u origin main
```
> ⚠️ `.gitignore` allaqachon `.env` ni chiqarib tashlaydi. `git status` da `.env` **ko'rinmasligi** kerak — API kalitlaringiz GitHub'ga chiqmasin.

---

## 2. Oracle Security List — 80/443 portlarini ochish (BRAUZERDAN)
Bu qadam **majburiy**, aks holda sayt tashqaridan ochilmaydi.

OCI Console → **Networking → Virtual Cloud Networks → (VCN'ingiz) → Security Lists → Default Security List → Add Ingress Rules**:

| Source CIDR | IP Protocol | Destination Port |
|-------------|-------------|------------------|
| `0.0.0.0/0` | TCP | `80` |
| `0.0.0.0/0` | TCP | `443` |

(SSH uchun 22-port odatda ochiq.)

---

## 3. DNS — domenni serverga yo'naltirish
Domen provayderingizda A-record qo'shing:
```
ai.alsamos.com   A   <SERVER_PUBLIC_IP>
```
Server IP'sini OCI panelida instansiya sahifasida (Public IP) ko'rasiz.

---

## 4. Serverga ulanib, avtomatik sozlash
SSH orqali serverga kiring:
```bash
ssh ubuntu@<SERVER_PUBLIC_IP>
```
Keyin kodni oling va bitta skript bilan hammasini sozlang:
```bash
sudo apt-get update -y && sudo apt-get install -y git
git clone https://github.com/SamandarAlimov/alsamos-llm-web.git
cd alsamos-llm-web
sudo bash deploy/oracle-setup.sh
```

Skript avtomatik: Docker o'rnatadi → server ichki firewall'da 80/443 ochadi (Ubuntu OCI'dagi `iptables` muammosini ham hal qiladi) → `backend/.env` yaratadi (maxfiy kalitni o'zi generatsiya qiladi) → React'ni build qilib, Docker stack'ni ko'taradi.

---

## 5. API kalitni kiriting va qayta ishga tushiring
```bash
nano backend/.env
```
Kamida shularni to'ldiring:
```
OPENROUTER_API_KEY=sk-or-...        # majburiy (matn modellari uchun)
ALSAMOS_ACCESS_PASSWORD=kuchli-parol # tavsiya: saytni parol bilan yoping
```
Saqlang (Ctrl+O, Enter, Ctrl+X), so'ng:
```bash
docker compose up -d --build
```

---

## 6. Tekshirish
Bir-ikki daqiqadan so'ng (Caddy SSL olishi uchun) oching:

👉 **https://ai.alsamos.com**

Loglarni kuzatish:
```bash
docker compose logs -f
```

---

## Foydali buyruqlar
| Vazifa | Buyruq |
|--------|--------|
| Holat | `docker compose ps` |
| Loglar | `docker compose logs -f` |
| Yangilash (git'dan) | `git pull && docker compose up -d --build` |
| To'xtatish | `docker compose down` |
| Qayta ishga tushirish | `docker compose restart` |

---

## Muammolarni bartaraf etish
- **Sayt ochilmayapti / timeout** → 90% hollarda 2-qadam (Security List) yoki firewall. Tekshiring:
  - OCI Security List'da 80/443 ingress bormi?
  - Serverda: `sudo iptables -L INPUT -n | grep -E '80|443'` — ACCEPT ko'rinishi kerak.
- **SSL sertifikat olinmadi** → DNS hali tarqalmagan bo'lishi mumkin. `dig ai.alsamos.com` server IP'ni ko'rsatishini kuting, so'ng `docker compose restart caddy`.
- **502 Bad Gateway** → app konteyner hali ko'tarilmoqda yoki yiqilgan: `docker compose logs app`.
- **Modellar javob bermayapti** → `backend/.env` da `OPENROUTER_API_KEY` to'g'rimi tekshiring.

---

## ARM (Ampere) haqida eslatma
Ampere A1 shakli ARM64. Ishlatilgan `python:3.11-slim`, `node:20-slim` va `caddy:2` image'lari ARM64'ni qo'llab-quvvatlaydi — hech qanday o'zgartirish shart emas.
