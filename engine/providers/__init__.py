"""
AI Provider abstraction layer.

All AI providers must implement BaseAIProvider so that HybridClassifier
can swap between Gemini, HuggingFace, Transformers, and Ollama transparently.
"""

from abc import ABC, abstractmethod
from models.ticket import Ticket


class BaseAIProvider(ABC):
    """Abstract base class for all AI classification providers."""

    @abstractmethod
    def classify(self, ticket: Ticket) -> dict:
        """
        Classify a support ticket using an AI model.

        Args:
            ticket: The incoming Ticket dataclass instance.

        Returns:
            A dict with the following keys:
            {
                "category": "billing" | "account" | "technical" | "general",
                "priority": "high" | "medium" | "low",
                "reason": "<one-sentence explanation>",
                "confidence": <float 0.0 – 1.0>
            }

        Raises:
            Any exception on API/model failure — caught by HybridClassifier.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this provider is configured and reachable.
        HybridClassifier calls this before classify() to decide whether to attempt AI.
        """
