import re
from models.ticket import Ticket

class TicketEvaluator:
    CATEGORY_PRIORITY = {
        "billing": 3,
        "technical": 2,
        "account": 1,
        "general": 0,
    }

    def __init__(self, category_rules: dict, urgency_keywords: list, billing_urgency_keywords: list):
        """Initialize the evaluator with rules loaded from the database."""
        self.category_rules = category_rules
        self.urgency_keywords = urgency_keywords
        self.billing_urgency_keywords = billing_urgency_keywords

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

    def _score_category(self, subject: str, message: str, keywords: list) -> int:
        """Scores keyword matches: subject matches are worth 2, message matches are worth 1."""
        score = 0
        for keyword in keywords:
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, subject):
                score += 2
            if re.search(pattern, message):
                score += 1
        return score

    def _count_subject_matches(self, subject: str, keywords: list) -> int:
        """Counts subject keyword matches for category tie breaking."""
        return sum(
            1
            for keyword in keywords
            if re.search(rf"\b{re.escape(keyword)}\b", subject)
        )

    def _get_matched_keywords(self, subject: str, message: str, keywords: list) -> list:
        """Returns unique keywords that match either the subject or message."""
        matched = []
        for keyword in keywords:
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, subject) or re.search(pattern, message):
                matched.append(keyword)
        return matched

    def _build_category_analysis(self, ticket: Ticket) -> dict:
        """Builds the internal category scoring analysis used by public evaluators."""
        subject = (ticket.subject or "").lower()
        message = (ticket.message or "").lower()
        return {
            category: {
                "score": self._score_category(subject, message, keywords),
                "subject_matches": self._count_subject_matches(subject, keywords),
                "priority_rank": self.CATEGORY_PRIORITY.get(category, 0),
                "matched_keywords": self._get_matched_keywords(subject, message, keywords),
            }
            for category, keywords in self.category_rules.items()
        }

    def _category_rank(self, category: str, category_analysis: dict) -> tuple:
        return (
            category_analysis[category]["score"],
            category_analysis[category]["subject_matches"],
            category_analysis[category]["priority_rank"],
        )

    def evaluate_category_details(self, ticket: Ticket) -> dict:
        """
        Returns detailed category scoring metadata while preserving evaluate_category()
        as the backwards-compatible string-only API.
        """
        category_analysis = self._build_category_analysis(ticket)

        if not category_analysis:
            return {
                "category": "general",
                "scores": {},
                "matched_keywords": {},
                "secondary_categories": [],
            }

        best_category = max(
            category_analysis,
            key=lambda category: self._category_rank(category, category_analysis)
        )
        if category_analysis[best_category]["score"] == 0:
            best_category = "general"

        secondary_categories = [
            category
            for category, analysis in sorted(
                category_analysis.items(),
                key=lambda item: self._category_rank(item[0], category_analysis),
                reverse=True
            )
            if category != best_category and analysis["score"] > 0
        ]

        return {
            "category": best_category,
            "scores": {
                category: analysis["score"]
                for category, analysis in category_analysis.items()
            },
            "matched_keywords": {
                category: analysis["matched_keywords"]
                for category, analysis in category_analysis.items()
                if analysis["matched_keywords"]
            },
            "secondary_categories": secondary_categories,
        }

    def evaluate_category(self, ticket: Ticket) -> str:
        details = self.evaluate_category_details(ticket)
        return details["category"]

    def evaluate_priority(self, ticket: Ticket, category: str) -> str:
        text = self._get_combined_text(ticket)
        customer_type = (ticket.customer_type or "").lower()

        is_premium = customer_type == "premium"
        has_urgency = self._contains_keyword(text, self.urgency_keywords)
        has_billing_urgency = category == "billing" and self._contains_keyword(text, self.billing_urgency_keywords)

        if is_premium or has_urgency or has_billing_urgency:
            return "high"
            
        if category in ["technical", "account"]:
            return "medium"
            
        return "low"

    def _format_keyword_list(self, keywords: list) -> str:
        if not keywords:
            return ""
        if len(keywords) == 1:
            return keywords[0]
        return f"{', '.join(keywords[:-1])}, and {keywords[-1]}"

    def _build_category_reason(self, category: str, details: dict) -> str:
        matched_keywords = details.get("matched_keywords", {})
        primary_keywords = matched_keywords.get(category, [])

        if category == "general" and not primary_keywords:
            return "Classified as general because no category-specific keywords matched."

        if primary_keywords:
            primary_terms = self._format_keyword_list(primary_keywords)
            reason = f"Classified as {category} because {primary_terms} matched strongest."
        else:
            reason = f"Classified as {category} because it had the strongest category score."

        secondary_reasons = []
        for secondary_category in details.get("secondary_categories", []):
            secondary_keywords = matched_keywords.get(secondary_category, [])
            if secondary_keywords:
                secondary_terms = self._format_keyword_list(secondary_keywords)
                secondary_reasons.append(
                    f"Also detected {secondary_category}-related terms: {secondary_terms}."
                )

        if secondary_reasons:
            reason = f"{reason} {' '.join(secondary_reasons)}"

        return reason

    def _build_priority_reason(self, ticket: Ticket, category: str, priority: str) -> str:
        text = self._get_combined_text(ticket)
        customer_type = (ticket.customer_type or "").lower()

        if priority == "high":
            reasons = []
            if customer_type == "premium":
                reasons.append("customer is premium")
            if self._contains_keyword(text, self.urgency_keywords):
                reasons.append("ticket contains urgency keywords")
            if category == "billing" and self._contains_keyword(text, self.billing_urgency_keywords):
                reasons.append("billing ticket contains financial urgency keywords")

            if reasons:
                reasons_str = " and ".join(reasons)
                return f"Marked high priority because {reasons_str}."

        return f"Marked {priority} priority."

    def generate_reason(self, ticket: Ticket, category: str, priority: str) -> str:
        details = self.evaluate_category_details(ticket)
        category_reason = self._build_category_reason(category, details)
        priority_reason = self._build_priority_reason(ticket, category, priority)
        return f"{category_reason} {priority_reason}"
