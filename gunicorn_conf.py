"""Gunicorn production konfiguratsiyasi (uvicorn worker + SSE uchun moslashtirilgan)."""
import os

bind = f"0.0.0.0:{os.getenv('ALSAMOS_PORT', '8000')}"
# Eslatma: holat (metrics/knowledge) fayl asosida saqlanadi. Bitta instansiya
# uchun WEB_CONCURRENCY=1 eng izchil; ko'p worker'da fayllar umumiy volume'da.
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
worker_class = "uvicorn.workers.UvicornWorker"
timeout = int(os.getenv("ALSAMOS_TIMEOUT", "180"))  # SSE oqimlar uchun uzunroq
graceful_timeout = 30
keepalive = 15
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
