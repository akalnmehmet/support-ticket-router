"""
Central application configuration.
All environment variables are read from a single location.
"""

import os

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
