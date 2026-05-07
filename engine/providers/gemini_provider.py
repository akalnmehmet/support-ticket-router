"""
Google Gemini AI provider for ticket classification.

Uses the NEW google-genai SDK (google.genai) — the old google.generativeai is deprecated.
Free model: gemini-1.5-flash — 15 req/min, 1500 req/day on free tier.
"""

import json
import logging
import re

from google import genai
from google.genai import types

from engine.providers import BaseAIProvider
from models.ticket import Ticket

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """
You are a customer support ticket classification engine.
Given a ticket's subject, message, and customer type, classify it and return ONLY valid JSON.

Classification rules:
- billing   → keywords: payment, refund, invoice, money, card, charge, paid, withdrawn
- account   → keywords: login, password, account, access, authentication
- technical → keywords: crash, bug, error, upload, broken, not working, loading
- general   → fallback when no specific category matches

Priority rules:
- high   → customer is "premium", OR ticket contains urgency words (urgent, asap, blocked, cannot use),
           OR billing ticket with financial terms (money, refund, withdrawn, fraud)
- medium → category is "technical" or "account" (and no high conditions apply)
- low    → all other cases

Return ONLY this JSON structure, nothing else:
{
  "category": "billing" | "account" | "technical" | "general",
  "priority": "high" | "medium" | "low",
  "reason": "<one concise sentence explaining category and priority decision>",
  "confidence": <float between 0.0 and 1.0>
}
""".strip()


class GeminiProvider(BaseAIProvider):
    """Classifies tickets using Google Gemini (free tier, new google.genai SDK)."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash-lite"):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for GeminiProvider.")
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._available = True
        logger.info(f"GeminiProvider initialized with model '{model}'.")

    def is_available(self) -> bool:
        return self._available

    def classify(self, ticket: Ticket) -> dict:
        user_prompt = (
            f"Subject: {ticket.subject or ''}\n"
            f"Message: {ticket.message or ''}\n"
            f"Customer Type: {ticket.customer_type or 'standard'}"
        )

        response = self._client.models.generate_content(
            model=self._model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                temperature=0.1,   # low temperature = more deterministic JSON
            ),
        )

        raw = response.text.strip()

        # Strip markdown code fences if model wraps output in ```json ... ```
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)

        result = json.loads(raw)
        self._validate(result)
        return result

    @staticmethod
    def _validate(result: dict) -> None:
        """Ensures the returned dict has expected keys and valid values."""
        valid_categories = {"billing", "account", "technical", "general"}
        valid_priorities = {"high", "medium", "low"}

        if result.get("category") not in valid_categories:
            result["category"] = "general"
        if result.get("priority") not in valid_priorities:
            result["priority"] = "low"
        if not isinstance(result.get("confidence"), (int, float)):
            result["confidence"] = 0.5
        result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))
        if not result.get("reason"):
            result["reason"] = f"Classified as {result['category']} by AI."
