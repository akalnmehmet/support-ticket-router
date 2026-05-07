import json
import os
import logging
from dotenv import load_dotenv

from models.ticket import Ticket
from engine.evaluator import TicketEvaluator
from engine.router import TeamRouter
from engine.ai_classifier import HybridClassifier
from database.db import init_db, get_category_rules, get_team_mappings, get_priority_keywords
from config import settings

# Load .env before reading settings
load_dotenv()

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def _build_ai_provider():
    """
    Factory: reads AI_PROVIDER from settings and returns the matching provider instance.
    Returns None if AI_PROVIDER is 'none', the required key is missing, or the package
    is not installed (falls back to RegEx engine silently).
    """
    provider_name = (settings.AI_PROVIDER or "none").lower()

    if provider_name == "gemini":
        if not settings.GEMINI_API_KEY:
            logger.warning("AI_PROVIDER=gemini but GEMINI_API_KEY is empty. Falling back to RegEx.")
            return None
        try:
            from engine.providers.gemini_provider import GeminiProvider
            logger.info(f"AI Provider: Gemini ({settings.GEMINI_MODEL})")
            return GeminiProvider(settings.GEMINI_API_KEY, settings.GEMINI_MODEL)
        except ImportError as e:
            logger.warning(f"google-genai package not installed ({e}). Falling back to RegEx.")
            return None

    if provider_name == "huggingface":
        try:
            from engine.providers.huggingface_provider import HuggingFaceProvider
            logger.info("AI Provider: HuggingFace Inference API")
            return HuggingFaceProvider(settings.HF_API_TOKEN)
        except ImportError as e:
            logger.warning(f"huggingface_hub package not installed ({e}). Falling back to RegEx.")
            return None

    if provider_name == "transformers":
        try:
            from engine.providers.transformers_provider import TransformersProvider
            logger.info("AI Provider: Local Transformers (zero-shot)")
            return TransformersProvider()
        except ImportError as e:
            logger.warning(f"transformers/torch package not installed ({e}). Falling back to RegEx.")
            return None

    if provider_name == "ollama":
        try:
            from engine.providers.ollama_provider import OllamaProvider
            logger.info(f"AI Provider: Ollama ({settings.OLLAMA_MODEL})")
            return OllamaProvider(settings.OLLAMA_MODEL, settings.OLLAMA_URL)
        except ImportError as e:
            logger.warning(f"ollama package not installed ({e}). Falling back to RegEx.")
            return None

    logger.info("AI Provider: none — using RegEx engine only.")
    return None


def main(input_file_path="data/tickets.json", output_file_path="data/processed_tickets.json"):

    # ── Load Tickets ──────────────────────────────────────────────────────────
    if not os.path.exists(input_file_path):
        logger.error(f"Error: '{input_file_path}' not found.")
        return

    try:
        with open(input_file_path, 'r', encoding="utf-8") as f:
            raw_tickets = json.load(f)
        logger.info(f"Loaded {len(raw_tickets)} tickets from {input_file_path}")
    except Exception as e:
        logger.error(f"Error reading {input_file_path}: {e}")
        return

    # ── Init DB & Build Engine ────────────────────────────────────────────────
    init_db()
    category_rules = get_category_rules()
    team_mapping = get_team_mappings()
    urgency_keywords = get_priority_keywords("urgency")
    billing_urgency_keywords = get_priority_keywords("billing_urgency")

    evaluator = TicketEvaluator(category_rules, urgency_keywords, billing_urgency_keywords)
    router = TeamRouter(team_mapping)
    ai_provider = _build_ai_provider()

    classifier = HybridClassifier(
        evaluator=evaluator,
        router=router,
        ai_provider=ai_provider,
        confidence_threshold=settings.AI_CONFIDENCE_THRESHOLD,
    )

    # ── Process Tickets ───────────────────────────────────────────────────────
    output_data = []

    for t_data in raw_tickets:
        try:
            ticket = Ticket(
                id=t_data.get("id"),
                subject=t_data.get("subject", ""),
                message=t_data.get("message", ""),
                customer_type=t_data.get("customerType", "standard"),
                created_at=t_data.get("createdAt", "")
            )

            pt = classifier.process(ticket)

            # camelCase JSON output (matches assessment format)
            output_data.append({
                "id": pt.id,
                "category": pt.category,
                "priority": pt.priority,
                "assignedTeam": pt.assigned_team,
                "reason": pt.reason,
                "confidence": round(pt.confidence, 4),
                "aiUsed": pt.ai_used,
            })

        except Exception as e:
            logger.warning(f"Skipping invalid ticket data: {t_data} (Error: {e})")

    # ── Output ────────────────────────────────────────────────────────────────
    json_output = json.dumps(output_data, indent=2, ensure_ascii=False)
    print("\n--- Processed Tickets ---")
    print(json_output)

    try:
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        with open(output_file_path, 'w', encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully saved processed tickets to {output_file_path}")
    except Exception as e:
        logger.error(f"Failed to save output to {output_file_path}: {e}")


if __name__ == "__main__":
    main()
