"""
Local Transformers Provider — offline zero-shot classification.

Uses HuggingFace Transformers pipeline locally — no internet needed after
the first model download. Works on CPU (slow) or GPU (fast).

Model: MoritzLaurer/mDeBERTa-v3-base-mnli-xnli
  - Lighter than ModernBERT-large (~280MB vs ~560MB)
  - Good multilingual support
  - Runs on CPU in ~2-5 seconds per ticket

Install:
    pip install transformers torch

First run downloads the model (~280MB) to ~/.cache/huggingface/
"""

import logging
from engine.providers import BaseAIProvider
from models.ticket import Ticket

logger = logging.getLogger(__name__)

# Descriptive phrases improve zero-shot NLI accuracy vs bare category names
_CANDIDATE_LABELS = [
    "billing payment invoice refund money charge",
    "account login password access authentication",
    "technical crash bug error upload broken",
    "general inquiry other",
]

_LABEL_MAP = {
    "billing payment invoice refund money charge": "billing",
    "account login password access authentication": "account",
    "technical crash bug error upload broken": "technical",
    "general inquiry other": "general",
}

_URGENCY_WORDS = {"urgent", "asap", "immediately", "blocked", "cannot use", "emergency"}
_BILLING_URGENCY = {"money", "refund", "withdrawn", "fraud"}

# Default model — lighter & faster than ModernBERT-large for CPU inference
_DEFAULT_MODEL = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"


class TransformersProvider(BaseAIProvider):
    """
    Classifies tickets using a local zero-shot classification pipeline.
    Fully offline after initial model download.

    Args:
        model: HuggingFace model ID. Defaults to mDeBERTa-v3-base-mnli-xnli (~280MB).
        device: -1 = CPU, 0 = first GPU.
    """

    def __init__(self, model: str = _DEFAULT_MODEL, device: int = -1):
        try:
            from transformers import pipeline
            logger.info(f"Loading local model '{model}' (may take a moment on first run)...")
            self._pipeline = pipeline(
                "zero-shot-classification",
                model=model,
                device=device,
            )
            self._ready = True
            logger.info(f"TransformersProvider ready with model '{model}'.")
        except ImportError:
            self._pipeline = None
            self._ready = False
            logger.warning(
                "transformers/torch not installed. "
                "Run: pip install transformers torch"
            )
        except Exception as exc:
            self._pipeline = None
            self._ready = False
            logger.warning(f"TransformersProvider failed to load model: {exc}")

    def is_available(self) -> bool:
        return self._ready

    def classify(self, ticket: Ticket) -> dict:
        text = f"{ticket.subject or ''}. {ticket.message or ''}".strip(". ")

        output = self._pipeline(text, candidate_labels=_CANDIDATE_LABELS)

        best_phrase = output["labels"][0]
        confidence = float(output["scores"][0])
        category = _LABEL_MAP.get(best_phrase, "general")

        priority = self._infer_priority(ticket, category, text)
        reason = (
            f"Local AI model classified as {category} "
            f"with {confidence:.0%} confidence (offline inference)."
        )

        return {
            "category": category,
            "priority": priority,
            "reason": reason,
            "confidence": round(confidence, 4),
        }

    @staticmethod
    def _infer_priority(ticket: Ticket, category: str, text: str) -> str:
        customer_type = (ticket.customer_type or "").lower()
        text_lower = text.lower()

        if customer_type == "premium":
            return "high"
        if any(w in text_lower for w in _URGENCY_WORDS):
            return "high"
        if category == "billing" and any(w in text_lower for w in _BILLING_URGENCY):
            return "high"
        if category in ("technical", "account"):
            return "medium"
        return "low"
