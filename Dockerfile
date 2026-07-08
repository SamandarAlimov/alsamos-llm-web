# Alsamos LLM — production image (React build + Python runtime)

# ---- Stage 1: React (Vite) frontend build ----
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend-react/ ./
RUN npm install --no-audit --no-fund && npm run build

# ---- Stage 2: Python runtime ----
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    ALSAMOS_ENV=production \
    ALSAMOS_HOST=0.0.0.0

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --upgrade pip && pip install -r backend/requirements.txt

COPY backend ./backend
COPY frontend ./frontend
COPY gunicorn_conf.py ./gunicorn_conf.py

# React (Vite) build natijasi — backend buni ustun ravishda xizmat qiladi
COPY --from=frontend /fe/dist ./frontend-react/dist

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)"

CMD ["gunicorn", "-c", "gunicorn_conf.py", "backend.main:app"]
