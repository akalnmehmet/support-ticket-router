"""
Business rules configuration for support ticket routing.
"""

CATEGORY_RULES = {
    "billing": ["payment", "paid", "card", "invoice", "refund", "money"],
    "account": ["login", "password", "account", "access"],
    "technical": ["crash", "bug", "error", "upload", "broken", "not working"],
}

TEAM_ROUTING_RULES = {
    "billing": "payments-team",
    "account": "account-support",
    "technical": "technical-support",
    "general": "general-support",
}

URGENCY_KEYWORDS = [
    "urgent",
    "asap",
    "immediately",
    "cannot use",
    "blocked",
]

BILLING_URGENCY_KEYWORDS = [
    "money",
    "refund",
    "withdrawn",
]
