import os
import threading
from celery import Celery
from celery.signals import worker_process_init

from models.ticket import Ticket as InternalTicket
from engine.evaluator import TicketEvaluator
from engine.router import TeamRouter
from engine.notifier import send_webhook
from database.db import init_db, get_category_rules, get_team_mappings, get_priority_keywords, save_processed_ticket
from config.settings import REDIS_URL, CELERY_TASK_MAX_RETRIES, CELERY_TASK_RETRY_BACKOFF

celery_app = Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

import threading

# Thread-local storage for engine instances (safe for Celery concurrent workers)
_thread_local = threading.local()

def _get_engines():
    """Lazily initializes and caches engine instances per worker thread."""
    if not getattr(_thread_local, 'initialized', False):
        init_db()
        category_rules = get_category_rules()
        team_mapping = get_team_mappings()
        urgency_keywords = get_priority_keywords("urgency")
        billing_urgency_keywords = get_priority_keywords("billing_urgency")
        _thread_local.evaluator = TicketEvaluator(category_rules, urgency_keywords, billing_urgency_keywords)
        _thread_local.router = TeamRouter(team_mapping)
        _thread_local.initialized = True
    return _thread_local.evaluator, _thread_local.router

@celery_app.task(
    name="process_ticket",
    max_retries=CELERY_TASK_MAX_RETRIES,
    retry_backoff=CELERY_TASK_RETRY_BACKOFF
)
def process_ticket_task(ticket_data: dict) -> dict:
    """The background task that processes a single ticket."""
    evaluator, router = _get_engines()

    # Map raw dictionary to our strictly typed InternalTicket dataclass
    internal_ticket = InternalTicket(
        id=ticket_data.get("id"),
        subject=ticket_data.get("subject", ""),
        message=ticket_data.get("message", ""),
        customer_type=ticket_data.get("customerType", "standard"),
        created_at=ticket_data.get("createdAt", "")
    )

    # Execute core business logic
    category = evaluator.evaluate_category(internal_ticket)
    priority = evaluator.evaluate_priority(internal_ticket, category)
    team = router.route_ticket(category)
    reason = evaluator.generate_reason(internal_ticket, category, priority)

    # Return structured result to be stored in Redis Backend
    result_data = {
        "id": internal_ticket.id,
        "category": category,
        "priority": priority,
        "assignedTeam": team,
        "reason": reason
    }
    
    try:
        # Send Notification to the assigned team's webhook
        webhook_data = {**ticket_data, **result_data}
        send_webhook(team, webhook_data)
    except Exception as exc:
        # Webhook failure must never block or fail the task
        import logging
        logging.getLogger(__name__).error(f"Webhook send failed: {exc}")

    try:
        # Persist result to DB history (non-blocking; failure is logged, not raised)
        save_processed_ticket(ticket_data, result_data)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(f"Failed to persist processed ticket: {exc}")

    return result_data
