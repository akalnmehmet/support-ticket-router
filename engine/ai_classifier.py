"""
HybridClassifier — AI-first classification with automatic RegEx fallback.

Processing flow:
1. If an AI provider is configured and available, attempt AI classification.
2. If AI confidence >= threshold → return AI result.
3. If AI confidence < threshold, or AI fails → fall back to TicketEvaluator (RegEx).
4. Fallback is always safe: no AI provider = pure RegEx, identical to old behaviour.
"""

import logging
from models.ticket import Ticket, ProcessedTicket
from engine.evaluator import TicketEvaluator
from engine.router import TeamRouter
from engine.providers import BaseAIProvider

logger = logging.getLogger(__name__)


class HybridClassifier:
    """
    Combines an optional AI provider with the existing RegEx engine.

    Args:
        evaluator: The rule-based TicketEvaluator (unchanged).
        router: The TeamRouter for category → team mapping.
        ai_provider: An optional BaseAIProvider implementation. If None, pure RegEx is used.
        confidence_threshold: Minimum AI confidence to accept the AI result (default 0.65).
    """

    def __init__(
        self,
        evaluator: TicketEvaluator,
        router: TeamRouter,
        ai_provider: BaseAIProvider | None = None,
        confidence_threshold: float = 0.65,
    ):
        self.evaluator = evaluator
        self.router = router
        self.ai_provider = ai_provider
        self.confidence_threshold = confidence_threshold

    def process(self, ticket: Ticket) -> ProcessedTicket:
        """
        Classify and route a single ticket.

        Returns a ProcessedTicket with confidence and ai_used metadata.
        """
        # ── Try AI provider ──────────────────────────────────────────────────
        if self.ai_provider and self.ai_provider.is_available():
            try:
                result = self.ai_provider.classify(ticket)
                confidence = float(result.get("confidence", 0.0))

                if confidence >= self.confidence_threshold:
                    category = result["category"]
                    logger.info(
                        f"Ticket {ticket.id}: AI classified as '{category}' "
                        f"(confidence={confidence:.2f})."
                    )
                    return ProcessedTicket(
                        id=ticket.id,
                        category=category,
                        priority=result["priority"],
                        assigned_team=self.router.route_ticket(category),
                        reason=result["reason"],
                        confidence=confidence,
                        ai_used=True,
                    )

                logger.info(
                    f"Ticket {ticket.id}: AI confidence too low "
                    f"({confidence:.2f} < {self.confidence_threshold}), falling back to RegEx."
                )

            except Exception as exc:
                logger.warning(
                    f"Ticket {ticket.id}: AI provider raised an exception ({exc}), "
                    "falling back to RegEx."
                )

        # ── RegEx fallback (original behaviour, always safe) ─────────────────
        category = self.evaluator.evaluate_category(ticket)
        priority = self.evaluator.evaluate_priority(ticket, category)
        reason = self.evaluator.generate_reason(ticket, category, priority)

        logger.debug(f"Ticket {ticket.id}: RegEx classified as '{category}'.")

        return ProcessedTicket(
            id=ticket.id,
            category=category,
            priority=priority,
            assigned_team=self.router.route_ticket(category),
            reason=reason,
            confidence=1.0,   # RegEx is deterministic — treat as fully confident
            ai_used=False,
        )
