"""
Celery Worker — Async Ticket Processing Task

Uses HybridClassifier (AI-first, RegEx fallback) for classification.
AI provider is initialized once per worker process and cached in thread-local
storage for thread safety across concurrent Celery workers.
"""

import logging
import threading
from celery import Celery

from models.ticket import Ticket as InternalTicket
from engine.evaluator import TicketEvaluator
from engine.router import TeamRouter
from engine.ai_classifier import HybridClassifier
from engine.notifier import send_webhook
from database.db import (
    init_db, get_category_rules, get_team_mappings,
    get_priority_keywords, save_processed_ticket
)
from config.settings import (
    REDIS_URL, CELERY_TASK_MAX_RETRIES, CELERY_TASK_RETRY_BACKOFF,
    AI_PROVIDER, GEMINI_API_KEY, GEMINI_MODEL,
    HF_API_TOKEN, OLLAMA_MODEL, OLLAMA_URL,
    AI_CONFIDENCE_THRESHOLD,
)

logger = logging.getLogger(__name__)

celery_app = Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

# ── Thread-local engine cache ─────────────────────────────────────────────────
# Each Celery worker process gets its own classifier instance.
# Thread-local ensures safety when concurrency > 1.
_thread_local = threading.local()


def _build_ai_provider():
    """Factory — mirrors main.py._build_ai_provider() for worker context."""
    provider_name = (AI_PROVIDER or "none").lower()

    if provider_name == "gemini" and GEMINI_API_KEY:
        try:
            from engine.providers.gemini_provider import GeminiProvider
            logger.info(f"Worker AI Provider: Gemini ({GEMINI_MODEL})")
            return GeminiProvider(GEMINI_API_KEY, GEMINI_MODEL)
        except ImportError as e:
            logger.warning(f"google-genai not installed ({e}). Worker falling back to RegEx.")
            return None

    if provider_name == "huggingface":
        try:
            from engine.providers.huggingface_provider import HuggingFaceProvider
            logger.info("Worker AI Provider: HuggingFace")
            return HuggingFaceProvider(HF_API_TOKEN)
        except ImportError as e:
            logger.warning(f"huggingface_hub not installed ({e}). Worker falling back to RegEx.")
            return None

    if provider_name == "transformers":
        try:
            from engine.providers.transformers_provider import TransformersProvider
            logger.info("Worker AI Provider: Local Transformers")
            return TransformersProvider()
        except ImportError as e:
            logger.warning(f"transformers/torch not installed ({e}). Worker falling back to RegEx.")
            return None

    if provider_name == "ollama":
        try:
            from engine.providers.ollama_provider import OllamaProvider
            logger.info(f"Worker AI Provider: Ollama ({OLLAMA_MODEL})")
            return OllamaProvider(OLLAMA_MODEL, OLLAMA_URL)
        except ImportError as e:
            logger.warning(f"Ollama import failed ({e}). Worker falling back to RegEx.")
            return None

    logger.info("Worker AI Provider: none — RegEx only.")
    return None


def _get_classifier() -> HybridClassifier:
    """
    Lazily initializes and caches a HybridClassifier per worker thread.
    DB init + AI provider setup happens only once per process lifecycle.
    """
    if not getattr(_thread_local, "initialized", False):
        init_db()
        category_rules = get_category_rules()
        team_mapping = get_team_mappings()
        urgency_keywords = get_priority_keywords("urgency")
        billing_urgency_keywords = get_priority_keywords("billing_urgency")

        evaluator = TicketEvaluator(
            category_rules, urgency_keywords, billing_urgency_keywords
        )
        router = TeamRouter(team_mapping)
        ai_provider = _build_ai_provider()

        _thread_local.classifier = HybridClassifier(
            evaluator=evaluator,
            router=router,
            ai_provider=ai_provider,
            confidence_threshold=AI_CONFIDENCE_THRESHOLD,
        )
        _thread_local.initialized = True

    return _thread_local.classifier


# ── Celery Task ───────────────────────────────────────────────────────────────

@celery_app.task(
    name="process_ticket",
    max_retries=CELERY_TASK_MAX_RETRIES,
    retry_backoff=CELERY_TASK_RETRY_BACKOFF,
)
def process_ticket_task(ticket_data: dict) -> dict:
    """
    Background task: classifies a single ticket using HybridClassifier.

    Returns a dict with category, priority, assignedTeam, reason,
    confidence, and aiUsed — stored in Redis backend for the API to poll.
    """
    classifier = _get_classifier()

    ticket = InternalTicket(
        id=ticket_data.get("id"),
        subject=ticket_data.get("subject", ""),
        message=ticket_data.get("message", ""),
        customer_type=ticket_data.get("customerType", "standard"),
        created_at=ticket_data.get("createdAt", ""),
    )

    pt = classifier.process(ticket)

    result_data = {
        "id": pt.id,
        "category": pt.category,
        "priority": pt.priority,
        "assignedTeam": pt.assigned_team,
        "reason": pt.reason,
        "confidence": round(pt.confidence, 4),
        "aiUsed": pt.ai_used,
    }

    # ── Webhook notification ──────────────────────────────────────────────
    try:
        send_webhook(pt.assigned_team, {**ticket_data, **result_data})
    except Exception as exc:
        logger.error(f"Webhook send failed: {exc}")

    # ── Persist to DB ─────────────────────────────────────────────────────
    try:
        save_processed_ticket(ticket_data, result_data)
    except Exception as exc:
        logger.error(f"Failed to persist processed ticket: {exc}")

    return result_data
