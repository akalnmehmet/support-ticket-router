"""
Central application configuration.
All environment variables are read from a single location.
"""

import os
from dotenv import load_dotenv

# Load .env automatically wherever this module is imported
load_dotenv()

# ─── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
SQLITE_PATH: str = os.getenv("SQLITE_PATH", "data/rules.db")

# ─── Redis / Celery ───────────────────────────────────────────────────────────
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ─── Admin Panel ──────────────────────────────────────────────────────────────
ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")

# ─── Webhooks ─────────────────────────────────────────────────────────────────
DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")

# ─── Celery Task Config ───────────────────────────────────────────────────────
CELERY_TASK_MAX_RETRIES: int = int(os.getenv("CELERY_TASK_MAX_RETRIES", "3"))
CELERY_TASK_RETRY_BACKOFF: bool = os.getenv("CELERY_TASK_RETRY_BACKOFF", "true").lower() == "true"

# ─── AI Classification ────────────────────────────────────────────────────────
AI_PROVIDER: str = os.getenv("AI_PROVIDER", "none")
AI_CONFIDENCE_THRESHOLD: float = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.65"))

# Google Gemini
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# HuggingFace
HF_API_TOKEN: str = os.getenv("HF_API_TOKEN", "")

# Ollama
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
