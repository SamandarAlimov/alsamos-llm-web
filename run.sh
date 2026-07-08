#!/usr/bin/env bash
# Alsamos LLM — ishga tushirish skripti
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "→ Virtual muhit yaratilmoqda..."
  python3 -m venv .venv
fi
source .venv/bin/activate

echo "→ Kutubxonalar o'rnatilmoqda..."
pip install -q -r backend/requirements.txt

if [ ! -f "backend/.env" ]; then
  cp backend/.env.example backend/.env
  echo "⚠  backend/.env yaratildi — OPENROUTER_API_KEY qo'shing (bepul: https://openrouter.ai/keys)"
fi

echo "→ Alsamos LLM ishga tushmoqda → http://127.0.0.1:8000"
python -m backend.main
