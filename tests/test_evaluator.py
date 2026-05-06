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
        # Refund in the subject scores higher than password in the message.
        ticket = self.create_ticket(subject="Refund requested", message="I also forgot my password")
        category = self.evaluator.evaluate_category(ticket)
        self.assertEqual(category, "billing")

    # --- 4. Scored Multi-Category Conflict Behavior ---

    def test_multi_category_conflict_prefers_subject_signal_over_later_message_matches(self):
        """
        Subject matches are weighted higher than message matches:
        account wins because login + account in the subject score stronger than
        refund + payment in the message.
        """
        ticket = self.create_ticket(
            subject="Cannot login to my account",
            message="I also noticed a refund and payment issue."
        )

        category = self.evaluator.evaluate_category(ticket)

        self.assertEqual(category, "account")

    def test_multi_category_conflict_counts_stronger_later_category_signal(self):
        """
        All category matches are scored before choosing the primary category:
        several technical message matches beat a single billing subject match.
        """
        ticket = self.create_ticket(
            subject="Payment warning",
            message="The app crashes, shows an error, and upload is broken."
        )

        category = self.evaluator.evaluate_category(ticket)

        self.assertEqual(category, "technical")

    def test_multi_category_conflict_chooses_highest_total_score(self):
        """
        The highest total score wins across categories.
        """
        ticket = self.create_ticket(
            subject="Upload error after login",
            message="I cannot access my account and the app is broken."
        )

        category = self.evaluator.evaluate_category(ticket)

        self.assertEqual(category, "technical")

    def test_scoring_billing_three_keywords_beats_account_one_keyword(self):
        ticket = self.create_ticket(
            subject="Payment card issue",
            message="I need a refund and cannot login."
        )

        details = self.evaluator.evaluate_category_details(ticket)

        self.assertEqual(details["category"], "billing")
        self.assertEqual(details["scores"]["billing"], 5)
        self.assertEqual(details["scores"]["account"], 1)
        self.assertEqual(details["matched_keywords"]["billing"], ["refund", "payment", "card"])
        self.assertEqual(details["matched_keywords"]["account"], ["login"])

    def test_scoring_subject_account_beats_message_billing_due_to_subject_bonus(self):
        ticket = self.create_ticket(
            subject="Cannot login to account",
            message="There is a payment problem."
        )

        details = self.evaluator.evaluate_category_details(ticket)

        self.assertEqual(details["category"], "account")
        self.assertEqual(details["scores"]["account"], 4)
        self.assertEqual(details["scores"]["billing"], 1)

    def test_multi_category_conflict_tie_break_prefers_more_subject_matches(self):
        """
        When total scores tie, the category with more subject matches wins before
        category priority is considered.
        """
        ticket = self.create_ticket(
            subject="Login issue",
            message="The app has a crash and error."
        )

        category = self.evaluator.evaluate_category(ticket)

        self.assertEqual(category, "account")

    def test_multi_category_conflict_tie_break_uses_category_priority(self):
        """
        When total score and subject match count tie, category priority wins:
        billing > technical > account > general.
        """
        ticket = self.create_ticket(
            subject="Mixed issue",
            message="I saw a login problem and then a crash."
        )

        category = self.evaluator.evaluate_category(ticket)

        self.assertEqual(category, "technical")

    def test_scoring_equal_score_uses_priority_order(self):
        ticket = self.create_ticket(
            subject="Mixed issue",
            message="I saw a login problem and then a crash."
        )

        details = self.evaluator.evaluate_category_details(ticket)

        self.assertEqual(details["scores"]["account"], details["scores"]["technical"])
        self.assertEqual(details["category"], "technical")

    def test_multi_category_conflict_tie_break_falls_back_to_insertion_order(self):
        """
        If score, subject matches and category priority all tie, the earlier
        configured category remains the deterministic fallback.
        """
        evaluator = TicketEvaluator(
            {"shipping": ["delivery"], "returns": ["package"]},
            self.evaluator.urgency_keywords,
            self.evaluator.billing_urgency_keywords
        )
        ticket = self.create_ticket(
            subject="Mixed issue",
            message="The delivery and package details look wrong."
        )

        category = evaluator.evaluate_category(ticket)

        self.assertEqual(category, "shipping")

    # --- 5. Category Detail Analysis ---

    def test_evaluate_category_details_returns_scores_matches_and_secondary_categories(self):
        ticket = self.create_ticket(
            subject="Payment card issue",
            message="I cannot login and need a refund."
        )

        details = self.evaluator.evaluate_category_details(ticket)

        self.assertEqual(details["category"], "billing")
        self.assertEqual(details["scores"]["billing"], 5)
        self.assertEqual(details["scores"]["account"], 1)
        self.assertEqual(details["matched_keywords"]["billing"], ["refund", "payment", "card"])
        self.assertEqual(details["matched_keywords"]["account"], ["login"])
        self.assertEqual(details["secondary_categories"], ["account"])

    def test_evaluate_category_details_keeps_evaluate_category_backwards_compatible(self):
        ticket = self.create_ticket(
            subject="Upload error after login",
            message="I cannot access my account and the app is broken."
        )

        details = self.evaluator.evaluate_category_details(ticket)

        self.assertEqual(self.evaluator.evaluate_category(ticket), details["category"])

    def test_evaluate_category_details_returns_general_without_matches(self):
        ticket = self.create_ticket(subject="Hello", message="Just checking in.")

        details = self.evaluator.evaluate_category_details(ticket)

        self.assertEqual(details["category"], "general")
        self.assertTrue(all(score == 0 for score in details["scores"].values()))
        self.assertEqual(details["matched_keywords"], {})
        self.assertEqual(details["secondary_categories"], [])

    def test_scoring_no_match_returns_general(self):
        ticket = self.create_ticket(subject="Question", message="Just wanted to check something.")

        self.assertEqual(self.evaluator.evaluate_category(ticket), "general")

    def test_scoring_non_refundable_does_not_trigger_billing(self):
        ticket = self.create_ticket(
            subject="Product policy",
            message="I saw this item is non-refundable. Is that correct?"
        )

        details = self.evaluator.evaluate_category_details(ticket)

        self.assertEqual(details["category"], "general")
        self.assertEqual(details["scores"]["billing"], 0)
        self.assertNotIn("billing", details["matched_keywords"])

    # --- 6. Reason Generation ---

    def test_generate_reason_includes_primary_and_secondary_category_signals(self):
        ticket = self.create_ticket(
            subject="Payment card issue",
            message="I cannot login and need a refund.",
            customer_type="standard"
        )
        category = self.evaluator.evaluate_category(ticket)
        priority = self.evaluator.evaluate_priority(ticket, category)

        reason = self.evaluator.generate_reason(ticket, category, priority)

        self.assertIn("Classified as billing because refund, payment, and card matched strongest.", reason)
        self.assertIn("Also detected account-related terms: login.", reason)
        self.assertIn("Marked high priority because billing ticket contains financial urgency keywords.", reason)

    def test_generate_reason_explains_general_no_match(self):
        ticket = self.create_ticket(subject="Hello", message="Just checking in.")
        category = self.evaluator.evaluate_category(ticket)
        priority = self.evaluator.evaluate_priority(ticket, category)

        reason = self.evaluator.generate_reason(ticket, category, priority)

        self.assertEqual(
            reason,
            "Classified as general because no category-specific keywords matched. Marked low priority."
        )

if __name__ == '__main__':
    unittest.main()
