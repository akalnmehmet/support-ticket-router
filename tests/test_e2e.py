"""
End-to-End (E2E) Tests for the Support Ticket Router pipeline.

These tests simulate the full lifecycle of ticket processing:
    JSON input file → main() → JSON output file

All tests use isolated temporary databases (SQLite) to avoid polluting
production data and to run without a PostgreSQL server.
"""

import os
import json
import tempfile
import pytest
from unittest.mock import patch

from main import main


@pytest.fixture
def temp_env():
    """Provides isolated temporary paths for input, output and SQLite DB."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield {
            "input": os.path.join(temp_dir, "input.json"),
            "output": os.path.join(temp_dir, "output.json"),
            "db": os.path.join(temp_dir, "test.db"),
        }


def run_pipeline(paths: dict, tickets: list) -> list:
    """Helper: writes tickets to input file, runs pipeline, returns output list."""
    with open(paths["input"], "w") as f:
        json.dump(tickets, f)

    with patch("database.db.SQLITE_PATH", paths["db"]):
        main(input_file_path=paths["input"], output_file_path=paths["output"])

    with open(paths["output"], "r") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# 1. HAPPY PATH — Case Assessment Tickets
# ─────────────────────────────────────────────────────────────────────────────

class TestCaseAssessmentTickets:
    """Verifies that the 4 original assessment tickets produce the exact expected output."""

    def test_ticket_1_billing_high_premium(self, temp_env):
        """ID 1: Payment failed + money withdrawn + premium → billing, high, payments-team"""
        results = run_pipeline(temp_env, [{
            "id": 1,
            "subject": "Payment failed",
            "message": "My payment failed but money was withdrawn from my card.",
            "customerType": "premium",
            "createdAt": "2026-04-29T10:00:00Z"
        }])
        t = results[0]
        assert t["id"] == 1
        assert t["category"] == "billing"
        assert t["priority"] == "high"
        assert t["assignedTeam"] == "payments-team"

    def test_ticket_2_account_medium_standard(self, temp_env):
        """ID 2: Forgot password + standard → account, medium, account-support"""
        results = run_pipeline(temp_env, [{
            "id": 2,
            "subject": "Cannot login",
            "message": "I forgot my password and cannot access my account.",
            "customerType": "standard",
            "createdAt": "2026-04-29T10:05:00Z"
        }])
        t = results[0]
        assert t["id"] == 2
        assert t["category"] == "account"
        assert t["priority"] == "medium"
        assert t["assignedTeam"] == "account-support"

    def test_ticket_3_technical_medium_standard(self, temp_env):
        """ID 3: App crash + upload + standard → technical, medium, technical-support"""
        results = run_pipeline(temp_env, [{
            "id": 3,
            "subject": "App crashes",
            "message": "The mobile app crashes when I upload a photo.",
            "customerType": "standard",
            "createdAt": "2026-04-29T10:10:00Z"
        }])
        t = results[0]
        assert t["id"] == 3
        assert t["category"] == "technical"
        assert t["priority"] == "medium"
        assert t["assignedTeam"] == "technical-support"

    def test_ticket_4_billing_high_premium_refund(self, temp_env):
        """ID 4: Refund + invoice + premium → billing, high, payments-team"""
        results = run_pipeline(temp_env, [{
            "id": 4,
            "subject": "Refund request",
            "message": "I want a refund for my last invoice.",
            "customerType": "premium",
            "createdAt": "2026-04-29T10:15:00Z"
        }])
        t = results[0]
        assert t["id"] == 4
        assert t["category"] == "billing"
        assert t["priority"] == "high"
        assert t["assignedTeam"] == "payments-team"

    def test_all_four_tickets_together(self, temp_env, caplog):
        """Runs all 4 assessment tickets in a single batch and checks count + log output."""
        import logging
        caplog.set_level(logging.INFO)
        tickets = [
            {"id": 1, "subject": "Payment failed", "message": "My payment failed but money was withdrawn from my card.", "customerType": "premium", "createdAt": "2026-04-29T10:00:00Z"},
            {"id": 2, "subject": "Cannot login", "message": "I forgot my password and cannot access my account.", "customerType": "standard", "createdAt": "2026-04-29T10:05:00Z"},
            {"id": 3, "subject": "App crashes", "message": "The mobile app crashes when I upload a photo.", "customerType": "standard", "createdAt": "2026-04-29T10:10:00Z"},
            {"id": 4, "subject": "Refund request", "message": "I want a refund for my last invoice.", "customerType": "premium", "createdAt": "2026-04-29T10:15:00Z"},
        ]
        results = run_pipeline(temp_env, tickets)
        assert len(results) == 4
        assert "Loaded 4 tickets" in caplog.text
        assert "Successfully saved processed tickets" in caplog.text


# ─────────────────────────────────────────────────────────────────────────────
# 2. EDGE CASES
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgeCases:

    def test_empty_ticket_list(self, temp_env, caplog):
        """An empty input file should produce an empty output and not crash."""
        import logging
        caplog.set_level(logging.INFO)
        results = run_pipeline(temp_env, [])
        assert results == []
        assert "Loaded 0 tickets" in caplog.text

    def test_ticket_with_missing_optional_fields(self, temp_env):
        """Tickets missing optional fields should default gracefully."""
        results = run_pipeline(temp_env, [{
            "id": 99,
            "customerType": "standard"
            # subject and message both missing
        }])
        t = results[0]
        assert t["category"] == "general"
        assert t["priority"] == "low"
        assert t["assignedTeam"] == "general-support"

    def test_ticket_with_none_subject_and_message(self, temp_env):
        """None values for subject/message should not crash and default to general/low."""
        results = run_pipeline(temp_env, [{
            "id": 77,
            "subject": None,
            "message": None,
            "customerType": "standard",
            "createdAt": ""
        }])
        t = results[0]
        assert t["category"] == "general"
        assert t["priority"] == "low"

    def test_premium_general_inquiry_is_high_priority(self, temp_env):
        """Premium customers should always get high priority regardless of category."""
        results = run_pipeline(temp_env, [{
            "id": 55,
            "subject": "Hello",
            "message": "Just a general inquiry.",
            "customerType": "premium",
            "createdAt": ""
        }])
        t = results[0]
        assert t["category"] == "general"
        assert t["priority"] == "high"

    def test_urgency_keyword_overrides_low_priority(self, temp_env):
        """A standard customer using 'urgent' should be escalated to high priority."""
        results = run_pipeline(temp_env, [{
            "id": 66,
            "subject": "Problem",
            "message": "This is urgent please help immediately.",
            "customerType": "standard",
            "createdAt": ""
        }])
        t = results[0]
        assert t["priority"] == "high"

    def test_non_refundable_does_not_trigger_billing(self, temp_env):
        """
        'non-refundable' should NOT trigger the billing category.
        Regression test for regex word-boundary matching.
        """
        results = run_pipeline(temp_env, [{
            "id": 88,
            "subject": "Product inquiry",
            "message": "I saw this product is non-refundable. Is that correct?",
            "customerType": "standard",
            "createdAt": ""
        }])
        t = results[0]
        assert t["category"] == "general"

    def test_invalid_ticket_is_skipped_not_crashing(self, temp_env, caplog):
        """
        A batch with one completely invalid ticket and one valid ticket:
        the invalid one should be skipped with a warning, valid one processes fine.
        """
        import logging
        caplog.set_level(logging.WARNING)
        results = run_pipeline(temp_env, [
            "this_is_not_a_ticket_object",  # invalid entry
            {"id": 10, "subject": "Login issue", "message": "I forgot my password.", "customerType": "standard", "createdAt": ""}
        ])
        # Valid ticket should still be processed
        assert len(results) == 1
        assert results[0]["category"] == "account"


# ─────────────────────────────────────────────────────────────────────────────
# 3. OUTPUT FORMAT VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

class TestOutputFormat:

    def test_output_file_is_created(self, temp_env):
        """After running the pipeline, the output file must exist."""
        run_pipeline(temp_env, [
            {"id": 1, "subject": "Test", "message": "test message", "customerType": "standard", "createdAt": ""}
        ])
        assert os.path.exists(temp_env["output"])

    def test_output_contains_required_fields(self, temp_env):
        """Every processed ticket must have the 5 required output fields."""
        results = run_pipeline(temp_env, [
            {"id": 42, "subject": "Crash", "message": "app is broken", "customerType": "standard", "createdAt": ""}
        ])
        t = results[0]
        assert "id" in t
        assert "category" in t
        assert "priority" in t
        assert "assignedTeam" in t
        assert "reason" in t

    def test_priority_values_are_valid(self, temp_env):
        """Priority must always be one of: high, medium, low."""
        tickets = [
            {"id": 1, "subject": "billing issue", "message": "invoice problem", "customerType": "standard", "createdAt": ""},
            {"id": 2, "subject": "crash", "message": "broken app", "customerType": "standard", "createdAt": ""},
            {"id": 3, "subject": "hello", "message": "just saying hi", "customerType": "standard", "createdAt": ""},
        ]
        results = run_pipeline(temp_env, tickets)
        for t in results:
            assert t["priority"] in {"high", "medium", "low"}
