"""
HuggingFace Inference API provider for ticket classification.

Uses zero-shot classification via the serverless HuggingFace Inference API.
Free tier: ~a few hundred req/hour. No GPU needed — runs on HF infrastructure.

Model: MoritzLaurer/ModernBERT-large-zeroshot-v2.0
  - High-performance zero-shot NLI model
  - Works without any fine-tuning on support ticket data
  - Tested with the HF Inference API serverless endpoint
"""

import logging
from engine.providers import BaseAIProvider
from models.ticket import Ticket

logger = logging.getLogger(__name__)

# Descriptive label phrases improve zero-shot accuracy vs bare category names
_CANDIDATE_LABELS = [
    "billing payment invoice refund money charge",
    "account login password access authentication",
    "technical crash bug error upload broken",
    "general inquiry",
]

_LABEL_MAP = {
    "billing payment invoice refund money charge": "billing",
    "account login password access authentication": "account",
    "technical crash bug error upload broken": "technical",
    "general inquiry": "general",
}

_URGENCY_WORDS = {"urgent", "asap", "immediately", "blocked", "cannot use", "emergency"}


class HuggingFaceProvider(BaseAIProvider):
    """
    Classifies tickets using HuggingFace zero-shot classification (free serverless API).

    Args:
        api_token: HuggingFace API token (free at huggingface.co/settings/tokens).
                   Can be None for anonymous access (lower rate limit).
        model: HF model ID for zero-shot classification.
    """

    MODEL = "MoritzLaurer/ModernBERT-large-zeroshot-v2.0"

    def __init__(self, api_token: str = None, model: str = None):
        try:
            from huggingface_hub import InferenceClient
            self._client = InferenceClient(token=api_token or None)
            self._model = model or self.MODEL
            self._ready = True
            logger.info(f"HuggingFaceProvider initialized with model '{self._model}'.")
        except ImportError:
            self._ready = False
            logger.warning("huggingface_hub not installed. HuggingFaceProvider unavailable.")

    def is_available(self) -> bool:
        return self._ready

    def classify(self, ticket: Ticket) -> dict:
        text = f"{ticket.subject or ''}. {ticket.message or ''}".strip(". ")

        result = self._client.zero_shot_classification(
            text,
            candidate_labels=_CANDIDATE_LABELS,
            model=self._model,
        )

        # InferenceClient returns a ClassificationOutput object
        best_phrase = result.labels[0]
        confidence = float(result.scores[0])
        category = _LABEL_MAP.get(best_phrase, "general")

        priority = self._infer_priority(ticket, category, text)
        reason = (
            f"HuggingFace zero-shot model classified as {category} "
            f"with {confidence:.0%} confidence."
        )

        return {
            "category": category,
            "priority": priority,
            "reason": reason,
            "confidence": round(confidence, 4),
        }

    @staticmethod
    def _infer_priority(ticket: Ticket, category: str, text: str) -> str:
        """Mirror the same priority logic used by TicketEvaluator."""
        customer_type = (ticket.customer_type or "").lower()
        text_lower = text.lower()

        if customer_type == "premium":
            return "high"
        if any(w in text_lower for w in _URGENCY_WORDS):
            return "high"
        if category == "billing" and any(
            w in text_lower for w in {"money", "refund", "withdrawn", "fraud"}
        ):
            return "high"
        if category in ("technical", "account"):
            return "medium"
        return "low"
