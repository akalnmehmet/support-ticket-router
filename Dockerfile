# ── Stage 1: Base (shared deps) ───────────────────────────────────────────────
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required by psycopg2-binary
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# ── Stage 2: CLI (no Streamlit needed) ────────────────────────────────────────
FROM base AS cli
CMD ["python", "main.py"]

# ── Stage 3: API + Worker (default build target) ──────────────────────────────
FROM base AS api
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
