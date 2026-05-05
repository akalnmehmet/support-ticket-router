import unittest

from models.ticket import Ticket
from engine.evaluator import TicketEvaluator

class TestTicketEvaluator(unittest.TestCase):
    def setUp(self):
        """Initialize the TicketEvaluator with mock rules before each test."""
        category_rules = {
            "billing": ["refund", "invoice", "charge", "payment", "billing", "money", "paid", "card", "withdrawn"],
            "account": ["password", "login", "authentication", "account", "access"],
            "technical": ["crash", "bug", "error", "broken", "loading", "upload", "not working"],
        }
        urgency_keywords = ["urgent", "asap", "emergency", "immediately", "blocked", "cannot use"]
        billing_urgency_keywords = ["lawsuit", "legal", "fraud", "scam", "money", "withdrawn", "refund"]
        self.evaluator = TicketEvaluator(category_rules, urgency_keywords, billing_urgency_keywords)

    def create_ticket(self, subject="", message="", customer_type="standard"):
        """Helper method to easily construct a Ticket for testing."""
        return Ticket(
            id=1,
            subject=subject,
            message=message,
            customer_type=customer_type,
            created_at="2023-10-01T10:00:00Z"
        )

    # --- 1. Category Routing Tests ---

    def test_category_billing(self):
        ticket = self.create_ticket(subject="Need an invoice", message="Where is my refund?")
        self.assertEqual(self.evaluator.evaluate_category(ticket), "billing")

    def test_category_account(self):
        ticket = self.create_ticket(subject="Can't login", message="I forgot my password.")
        self.assertEqual(self.evaluator.evaluate_category(ticket), "account")

    def test_category_technical(self):
        ticket = self.create_ticket(subject="App crash", message="It is completely broken.")
        self.assertEqual(self.evaluator.evaluate_category(ticket), "technical")

    def test_category_general(self):
        ticket = self.create_ticket(subject="Hello", message="Just wanted to say hi.")
        self.assertEqual(self.evaluator.evaluate_category(ticket), "general")

    # --- 2. Priority Rules Tests ---

    def test_priority_high_premium_customer(self):
        ticket = self.create_ticket(customer_type="premium", message="General inquiry")
        self.assertEqual(self.evaluator.evaluate_priority(ticket, "general"), "high")

    def test_priority_high_urgency_keywords(self):
        ticket = self.create_ticket(message="I am totally blocked, fix this urgent issue!")
        self.assertEqual(self.evaluator.evaluate_priority(ticket, "general"), "high")

    def test_priority_medium_technical_account(self):
        ticket = self.create_ticket()
        self.assertEqual(self.evaluator.evaluate_priority(ticket, "technical"), "medium")
        self.assertEqual(self.evaluator.evaluate_priority(ticket, "account"), "medium")

    def test_priority_low_general(self):
        ticket = self.create_ticket()
        self.assertEqual(self.evaluator.evaluate_priority(ticket, "general"), "low")

    # --- 3. Edge Cases Tests ---

    def test_case_insensitivity(self):
        ticket = self.create_ticket(subject="URGENT", message="My PaYmEnT failed")
        
        category = self.evaluator.evaluate_category(ticket)
        self.assertEqual(category, "billing")
        
        priority = self.evaluator.evaluate_priority(ticket, category)
        self.assertEqual(priority, "high")

    def test_empty_fields(self):
        # Empty fields should be handled gracefully without crashing
        ticket = self.create_ticket(subject=None, message=None, customer_type=None)
        
        category = self.evaluator.evaluate_category(ticket)
        self.assertEqual(category, "general")
        
        priority = self.evaluator.evaluate_priority(ticket, category)
        self.assertEqual(priority, "low")

    def test_multiple_keywords(self):
        # If there are multiple keywords, it should still process it correctly.
        # Refund (billing) and Password (account). Billing is checked first based on dict order.
        ticket = self.create_ticket(subject="Refund requested", message="I also forgot my password")
        category = self.evaluator.evaluate_category(ticket)
        self.assertEqual(category, "billing")

if __name__ == '__main__':
    unittest.main()
