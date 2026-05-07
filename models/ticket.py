from dataclasses import dataclass, field


@dataclass
class Ticket:
    """
    Represents an incoming support ticket.

    Attributes:
        id (int): Unique identifier for the ticket.
        subject (str): The subject line or brief summary of the ticket.
        message (str): The detailed content or body of the ticket.
        customer_type (str): The classification of the customer (e.g., 'Enterprise', 'Standard').
        created_at (str): The timestamp of when the ticket was created.
    """
    id: int
    subject: str
    message: str
    customer_type: str
    created_at: str


@dataclass
class ProcessedTicket:
    """
    Represents a support ticket after it has been processed and classified by the routing engine.

    Attributes:
        id (int): Unique identifier for the ticket, matching the original Ticket ID.
        category (str): The categorized issue type of the ticket.
        priority (str): The assigned priority level (e.g., 'High', 'Medium', 'Low').
        assigned_team (str): The specific team designated to handle the ticket.
        reason (str): The justification for the assigned category, priority, and team.
        confidence (float): AI confidence score (0.0–1.0). 1.0 for rule-based fallback.
        ai_used (bool): True if an AI provider classified this ticket, False if RegEx was used.
    """
    id: int
    category: str
    priority: str
    assigned_team: str
    reason: str
    confidence: float = 1.0
    ai_used: bool = False
