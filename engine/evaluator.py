import re
from models.ticket import Ticket
from config.rules import CATEGORY_RULES, URGENCY_KEYWORDS, BILLING_URGENCY_KEYWORDS

class TicketEvaluator:
    def _get_combined_text(self, ticket: Ticket) -> str:
        """Helper method to safely extract and combine the subject and message in lowercase."""
        subject = ticket.subject if ticket.subject else ""
        message = ticket.message if ticket.message else ""
        return f"{subject} {message}".lower()

    def _contains_keyword(self, text: str, keywords: list) -> bool:
        """Helper method to check if any keyword exists as a whole word in the text using Regex."""
        for keyword in keywords:
            # \b matches word boundaries to ensure we don't match sub-words (e.g., 'refund' in 'non-refundable')
            if re.search(rf"\b{re.escape(keyword)}\b", text):
                return True
        return False

    def evaluate_category(self, ticket: Ticket) -> str:
        text = self._get_combined_text(ticket)
        
        for category, keywords in CATEGORY_RULES.items():
            if self._contains_keyword(text, keywords):
                return category
                    
        return "general"

    def evaluate_priority(self, ticket: Ticket, category: str) -> str:
        text = self._get_combined_text(ticket)
        customer_type = (ticket.customer_type or "").lower()

        is_premium = customer_type == "premium"
        has_urgency = self._contains_keyword(text, URGENCY_KEYWORDS)
        has_billing_urgency = category == "billing" and self._contains_keyword(text, BILLING_URGENCY_KEYWORDS)

        if is_premium or has_urgency or has_billing_urgency:
            return "high"
            
        if category in ["technical", "account"]:
            return "medium"
            
        return "low"

    def generate_reason(self, ticket: Ticket, category: str, priority: str) -> str:
        text = self._get_combined_text(ticket)
        customer_type = (ticket.customer_type or "").lower()

        if priority == "high":
            reasons = []
            if customer_type == "premium":
                reasons.append("customer is premium")
            if self._contains_keyword(text, URGENCY_KEYWORDS):
                reasons.append("ticket contains urgency keywords")
            if category == "billing" and self._contains_keyword(text, BILLING_URGENCY_KEYWORDS):
                reasons.append("billing ticket contains financial urgency keywords")
            
            if reasons:
                reasons_str = " and ".join(reasons)
                return f"Classified as {category} and marked high priority because {reasons_str}."

        return f"Classified as {category} with {priority} priority."
