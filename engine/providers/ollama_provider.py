"""
Ollama Provider — local LLM classification via the Ollama REST API.

Ollama runs open-source LLMs (Llama, Mistral, Phi, Qwen, etc.) entirely on your
machine. No API key, no internet required after model download, no token costs.

Setup:
    1. Install Ollama: https://ollama.com
    2. Pull a model: ollama pull llama3.2
    3. Set in .env: AI_PROVIDER=ollama, OLLAMA_MODEL=llama3.2

Recommended models (fast on CPU):
    - phi4-mini        (~2.5GB)  — Microsoft, excellent reasoning
    - llama3.2         (~2.0GB)  — Meta, great general purpose
    - qwen2.5:3b       (~1.9GB)  — Alibaba, very fast
    - gemma3:1b        (~815MB)  — Google, ultra-lightweight
"""

import json
import logging
import re

import requests

from engine.providers import BaseAIProvider
from models.ticket import Ticket

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a customer support ticket classifier.
Given a ticket's subject, message, and customer type, return ONLY valid JSON.

Classification rules:
- billing   → payment, refund, invoice, money, card, charge, paid, withdrawn
- account   → login, password, account, access, authentication
- technical → crash, bug, error, upload, broken, not working, loading
- general   → anything else

Priority rules:
- high   → customer is "premium" OR urgency words (urgent, asap, blocked) OR billing+financial terms
- medium → category is "technical" or "account"
- low    → all other cases

Return ONLY this JSON, no other text:
{"category": "billing|account|technical|general", "priority": "high|medium|low", "reason": "<one sentence>", "confidence": <0.0-1.0>}"""

_VALID_CATEGORIES = {"billing", "account", "technical", "general"}
_VALID_PRIORITIES  = {"high", "medium", "low"}


class OllamaProvider(BaseAIProvider):
    """
    Classifies tickets using a locally running Ollama LLM.

    Args:
        model: Ollama model name (e.g. 'llama3.2', 'phi4-mini', 'qwen2.5:3b').
        base_url: Ollama server URL (default: http://localhost:11434).
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434",
        timeout: int = 60,
    ):
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        logger.info(f"OllamaProvider configured: model='{model}', url='{base_url}'.")

    def is_available(self) -> bool:
        """Returns True if the Ollama server is reachable."""
        try:
            r = requests.get(f"{self._base_url}/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def classify(self, ticket: Ticket) -> dict:
        prompt = (
            f"Subject: {ticket.subject or ''}\n"
            f"Message: {ticket.message or ''}\n"
            f"Customer Type: {ticket.customer_type or 'standard'}"
        )

        payload = {
            "model": self._model,
            "prompt": prompt,
            "system": _SYSTEM_PROMPT,
            "stream": False,
            "format": "json",   # Ollama structured output mode
            "options": {"temperature": 0.1},
        }

        response = requests.post(
            f"{self._base_url}/api/generate",
            json=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()

        raw = response.json().get("response", "")

        # Strip any accidental markdown fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)

        result = json.loads(raw)
        self._validate(result)
        return result

    @staticmethod
    def _validate(result: dict) -> None:
        """Normalize and clamp values to prevent downstream errors."""
        if result.get("category") not in _VALID_CATEGORIES:
            result["category"] = "general"
        if result.get("priority") not in _VALID_PRIORITIES:
            result["priority"] = "low"
        if not isinstance(result.get("confidence"), (int, float)):
            result["confidence"] = 0.75
        result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))
        if not result.get("reason"):
            result["reason"] = f"Classified as {result['category']} by local LLM."
