"""
AI Classifier Test Suite — Faz 9

Tests for HybridClassifier + provider abstraction.
Uses unittest.mock so no real API calls are made — tests are fast and offline.

Run:
    pytest tests/test_ai_classifier.py -v
"""

import pytest
from unittest.mock import MagicMock, patch

from models.ticket import Ticket, ProcessedTicket
from engine.ai_classifier import HybridClassifier
from engine.evaluator import TicketEvaluator
from engine.router import TeamRouter


# ── Fixtures ──────────────────────────────────────────────────────────────────

CATEGORY_RULES = {
    "billing":   ["payment", "refund", "invoice", "money", "card", "charge", "paid", "withdrawn"],
    "account":   ["login", "password", "account", "access", "authentication"],
    "technical": ["crash", "bug", "error", "broken", "loading", "upload", "not working"],
}
TEAM_MAPPING = {
    "billing":   "payments-team",
    "account":   "account-support",
    "technical": "technical-support",
    "general":   "general-support",
}
URGENCY_KEYWORDS = ["urgent", "asap", "emergency", "immediately", "blocked", "cannot use"]
BILLING_URGENCY  = ["lawsuit", "legal", "fraud", "scam", "money", "withdrawn", "refund"]


@pytest.fixture
def evaluator():
    return TicketEvaluator(CATEGORY_RULES, URGENCY_KEYWORDS, BILLING_URGENCY)


@pytest.fixture
def router():
    return TeamRouter(TEAM_MAPPING)


@pytest.fixture
def billing_ticket():
    return Ticket(
        id=1,
        subject="Payment failed",
        message="My payment failed but money was withdrawn from my card.",
        customer_type="premium",
        created_at="2026-04-29T10:00:00Z",
    )


@pytest.fixture
def account_ticket():
    return Ticket(
        id=2,
        subject="Cannot login",
        message="I forgot my password and cannot access my account.",
        customer_type="standard",
        created_at="2026-04-29T10:05:00Z",
    )


@pytest.fixture
def general_ticket():
    return Ticket(
        id=5,
        subject="General inquiry",
        message="Hello, I have a question about your services.",
        customer_type="standard",
        created_at="2026-04-29T10:30:00Z",
    )


def _make_mock_provider(category="billing", priority="high",
                        reason="AI test", confidence=0.9, available=True):
    provider = MagicMock()
    provider.is_available.return_value = available
    provider.classify.return_value = {
        "category": category,
        "priority": priority,
        "reason": reason,
        "confidence": confidence,
    }
    return provider


# ── HybridClassifier — AI path ─────────────────────────────────────────────

class TestHybridClassifierAIPath:

    def test_uses_ai_when_confident(self, evaluator, router, billing_ticket):
        """AI result is accepted when confidence >= threshold."""
        provider = _make_mock_provider(category="billing", confidence=0.95)
        classifier = HybridClassifier(evaluator, router, provider, confidence_threshold=0.65)
        result = classifier.process(billing_ticket)

        assert result.ai_used is True
        assert result.category == "billing"
        assert result.priority == "high"
        assert result.assigned_team == "payments-team"
        assert result.confidence == 0.95

    def test_ai_used_flag_is_true(self, evaluator, router, account_ticket):
        provider = _make_mock_provider(category="account", priority="medium", confidence=0.80)
        classifier = HybridClassifier(evaluator, router, provider, confidence_threshold=0.65)
        result = classifier.process(account_ticket)

        assert result.ai_used is True

    def test_ai_reason_is_preserved(self, evaluator, router, billing_ticket):
        custom_reason = "AI detected financial urgency."
        provider = _make_mock_provider(reason=custom_reason, confidence=0.88)
        classifier = HybridClassifier(evaluator, router, provider, confidence_threshold=0.65)
        result = classifier.process(billing_ticket)

        assert result.reason == custom_reason

    def test_assigned_team_is_from_router_not_ai(self, evaluator, router, billing_ticket):
        """Even when AI classifies, team assignment goes through TeamRouter."""
        provider = _make_mock_provider(category="technical", confidence=0.90)
        classifier = HybridClassifier(evaluator, router, provider, confidence_threshold=0.65)
        result = classifier.process(billing_ticket)

        assert result.assigned_team == "technical-support"

    def test_general_category_routes_to_general_support(self, evaluator, router, general_ticket):
        provider = _make_mock_provider(category="general", priority="low", confidence=0.75)
        classifier = HybridClassifier(evaluator, router, provider, confidence_threshold=0.65)
        result = classifier.process(general_ticket)

        assert result.assigned_team == "general-support"


# ── HybridClassifier — Fallback path ──────────────────────────────────────

class TestHybridClassifierFallback:

    def test_falls_back_when_confidence_too_low(self, evaluator, router, billing_ticket):
        """Low-confidence AI result → RegEx engine takes over."""
        provider = _make_mock_provider(category="general", confidence=0.40)
        classifier = HybridClassifier(evaluator, router, provider, confidence_threshold=0.65)
        result = classifier.process(billing_ticket)

        # RegEx correctly classifies billing ticket
        assert result.ai_used is False
        assert result.category == "billing"

    def test_falls_back_when_provider_raises_exception(self, evaluator, router, billing_ticket):
        """Provider exceptions are caught and RegEx fallback is used."""
        provider = MagicMock()
        provider.is_available.return_value = True
        provider.classify.side_effect = RuntimeError("API timeout")

        classifier = HybridClassifier(evaluator, router, provider, confidence_threshold=0.65)
        result = classifier.process(billing_ticket)

        assert result.ai_used is False
        assert result.category == "billing"  # RegEx still correct

    def test_falls_back_when_provider_unavailable(self, evaluator, router, account_ticket):
        provider = _make_mock_provider(available=False)
        classifier = HybridClassifier(evaluator, router, provider, confidence_threshold=0.65)
        result = classifier.process(account_ticket)

        assert result.ai_used is False
        assert result.category == "account"

    def test_no_provider_uses_regex_only(self, evaluator, router, account_ticket):
        """None provider → pure RegEx, backward compatible."""
        classifier = HybridClassifier(evaluator, router, ai_provider=None)
        result = classifier.process(account_ticket)

        assert result.ai_used is False
        assert result.category == "account"
        assert result.confidence == 1.0  # deterministic regex

    def test_fallback_confidence_is_1(self, evaluator, router, billing_ticket):
        """RegEx fallback always reports confidence=1.0 (deterministic)."""
        classifier = HybridClassifier(evaluator, router, ai_provider=None)
        result = classifier.process(billing_ticket)

        assert result.confidence == 1.0

    def test_fallback_result_has_all_required_fields(self, evaluator, router, account_ticket):
        classifier = HybridClassifier(evaluator, router, ai_provider=None)
        result = classifier.process(account_ticket)

        assert hasattr(result, "id")
        assert hasattr(result, "category")
        assert hasattr(result, "priority")
        assert hasattr(result, "assigned_team")
        assert hasattr(result, "reason")
        assert hasattr(result, "confidence")
        assert hasattr(result, "ai_used")


# ── HybridClassifier — Threshold edge cases ───────────────────────────────

class TestHybridClassifierThreshold:

    def test_exactly_at_threshold_uses_ai(self, evaluator, router, billing_ticket):
        """confidence == threshold should be accepted (>=, not >)."""
        provider = _make_mock_provider(confidence=0.65)
        classifier = HybridClassifier(evaluator, router, provider, confidence_threshold=0.65)
        result = classifier.process(billing_ticket)

        assert result.ai_used is True

    def test_just_below_threshold_uses_regex(self, evaluator, router, billing_ticket):
        provider = _make_mock_provider(confidence=0.64)
        classifier = HybridClassifier(evaluator, router, provider, confidence_threshold=0.65)
        result = classifier.process(billing_ticket)

        assert result.ai_used is False

    def test_zero_threshold_always_uses_ai(self, evaluator, router, billing_ticket):
        """threshold=0.0 → always accept AI result, even if confidence is very low."""
        provider = _make_mock_provider(confidence=0.01)
        classifier = HybridClassifier(evaluator, router, provider, confidence_threshold=0.0)
        result = classifier.process(billing_ticket)

        assert result.ai_used is True

    def test_threshold_one_always_uses_regex(self, evaluator, router, billing_ticket):
        """threshold=1.0 → AI must be 100% confident, otherwise falls back."""
        provider = _make_mock_provider(confidence=0.99)
        classifier = HybridClassifier(evaluator, router, provider, confidence_threshold=1.0)
        result = classifier.process(billing_ticket)

        assert result.ai_used is False


# ── ProcessedTicket — new fields ──────────────────────────────────────────

class TestProcessedTicketFields:

    def test_default_confidence_is_1(self):
        pt = ProcessedTicket(id=1, category="billing", priority="high",
                             assigned_team="payments-team", reason="test")
        assert pt.confidence == 1.0

    def test_default_ai_used_is_false(self):
        pt = ProcessedTicket(id=1, category="billing", priority="high",
                             assigned_team="payments-team", reason="test")
        assert pt.ai_used is False

    def test_custom_confidence_set(self):
        pt = ProcessedTicket(id=1, category="billing", priority="high",
                             assigned_team="payments-team", reason="test", confidence=0.87)
        assert pt.confidence == 0.87

    def test_ai_used_can_be_true(self):
        pt = ProcessedTicket(id=1, category="billing", priority="high",
                             assigned_team="payments-team", reason="test", ai_used=True)
        assert pt.ai_used is True


# ── BaseAIProvider — contract ─────────────────────────────────────────────

class TestBaseAIProviderContract:

    def test_cannot_instantiate_abstract_class(self):
        from engine.providers import BaseAIProvider
        with pytest.raises(TypeError):
            BaseAIProvider()

    def test_mock_satisfies_interface(self, evaluator, router, billing_ticket):
        """A properly mocked provider works end-to-end with HybridClassifier."""
        provider = _make_mock_provider(confidence=0.85)
        classifier = HybridClassifier(evaluator, router, provider, confidence_threshold=0.65)
        result = classifier.process(billing_ticket)
        assert isinstance(result, ProcessedTicket)


# ── OllamaProvider — unit tests ───────────────────────────────────────────

class TestOllamaProvider:

    def test_is_unavailable_when_server_down(self):
        """is_available() returns False when Ollama server is not running."""
        from engine.providers.ollama_provider import OllamaProvider
        provider = OllamaProvider(base_url="http://localhost:19999")  # wrong port
        assert provider.is_available() is False

    def test_classify_returns_correct_structure(self, billing_ticket):
        """Mock the requests.post to verify JSON parsing and validation."""
        from engine.providers.ollama_provider import OllamaProvider
        import json

        mock_response_body = json.dumps({
            "category": "billing",
            "priority": "high",
            "reason": "Financial issue detected.",
            "confidence": 0.88,
        })

        with patch("engine.providers.ollama_provider.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"response": mock_response_body}
            mock_post.return_value.raise_for_status.return_value = None

            provider = OllamaProvider(model="llama3.2")
            result = provider.classify(billing_ticket)

        assert result["category"] == "billing"
        assert result["priority"] == "high"
        assert result["confidence"] == 0.88

    def test_validate_fixes_invalid_category(self, billing_ticket):
        """_validate() replaces unknown categories with 'general'."""
        from engine.providers.ollama_provider import OllamaProvider
        import json

        bad_response = json.dumps({
            "category": "unknown_cat",
            "priority": "high",
            "reason": "test",
            "confidence": 0.7,
        })

        with patch("engine.providers.ollama_provider.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"response": bad_response}
            mock_post.return_value.raise_for_status.return_value = None

            provider = OllamaProvider()
            result = provider.classify(billing_ticket)

        assert result["category"] == "general"

    def test_validate_clamps_confidence_above_1(self, billing_ticket):
        from engine.providers.ollama_provider import OllamaProvider
        import json

        bad_conf = json.dumps({
            "category": "billing", "priority": "high",
            "reason": "test", "confidence": 1.5,
        })

        with patch("engine.providers.ollama_provider.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"response": bad_conf}
            mock_post.return_value.raise_for_status.return_value = None

            provider = OllamaProvider()
            result = provider.classify(billing_ticket)

        assert result["confidence"] == 1.0

    def test_ollama_integrates_with_hybrid_classifier(
        self, evaluator, router, billing_ticket
    ):
        """Full integration: OllamaProvider + HybridClassifier."""
        from engine.providers.ollama_provider import OllamaProvider
        import json

        mock_body = json.dumps({
            "category": "billing", "priority": "high",
            "reason": "Ollama detected billing.", "confidence": 0.91,
        })

        with patch("engine.providers.ollama_provider.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"response": mock_body}
            mock_post.return_value.raise_for_status.return_value = None

            with patch("engine.providers.ollama_provider.requests.get") as mock_get:
                mock_get.return_value.status_code = 200

                provider = OllamaProvider()
                classifier = HybridClassifier(
                    evaluator, router, provider, confidence_threshold=0.65
                )
                result = classifier.process(billing_ticket)

        assert result.ai_used is True
        assert result.category == "billing"
        assert result.assigned_team == "payments-team"


# ── TransformersProvider — unit tests ────────────────────────────────────

class TestTransformersProvider:

    def test_unavailable_when_transformers_not_installed(self):
        """If transformers/torch missing, provider gracefully reports unavailable."""
        import unittest.mock
        with unittest.mock.patch.dict("sys.modules", {"transformers": None}):
            # Re-import inside the mock context
            import importlib
            import engine.providers.transformers_provider as tp_module
            importlib.reload(tp_module)
            provider = tp_module.TransformersProvider.__new__(
                tp_module.TransformersProvider
            )
            provider._pipeline = None
            provider._ready = False
            assert provider.is_available() is False

    def test_classify_returns_valid_structure(self, billing_ticket):
        """Mock the pipeline to verify label mapping and priority inference."""
        from engine.providers.transformers_provider import TransformersProvider

        mock_pipeline_output = {
            "labels": [
                "billing payment invoice refund money charge",
                "general inquiry other",
                "technical crash bug error upload broken",
                "account login password access authentication",
            ],
            "scores": [0.87, 0.06, 0.04, 0.03],
        }

        provider = TransformersProvider.__new__(TransformersProvider)
        provider._pipeline = MagicMock(return_value=mock_pipeline_output)
        provider._ready = True

        result = provider.classify(billing_ticket)

        assert result["category"] == "billing"
        assert result["priority"] == "high"   # premium customer → high
        assert result["confidence"] == 0.87

    def test_priority_medium_for_technical_standard(self):
        """Standard customer + technical category → medium priority."""
        from engine.providers.transformers_provider import TransformersProvider

        technical_ticket = Ticket(
            id=99, subject="App crash", message="The app crashes on load.",
            customer_type="standard", created_at="2026-04-29T12:00:00Z"
        )
        mock_output = {
            "labels": ["technical crash bug error upload broken", "general inquiry other"],
            "scores": [0.82, 0.18],
        }

        provider = TransformersProvider.__new__(TransformersProvider)
        provider._pipeline = MagicMock(return_value=mock_output)
        provider._ready = True

        result = provider.classify(technical_ticket)

        assert result["category"] == "technical"
        assert result["priority"] == "medium"

    def test_transformers_integrates_with_hybrid_classifier(
        self, evaluator, router, account_ticket
    ):
        from engine.providers.transformers_provider import TransformersProvider

        mock_output = {
            "labels": [
                "account login password access authentication",
                "general inquiry other",
            ],
            "scores": [0.79, 0.21],
        }

        provider = TransformersProvider.__new__(TransformersProvider)
        provider._pipeline = MagicMock(return_value=mock_output)
        provider._ready = True

        classifier = HybridClassifier(
            evaluator, router, provider, confidence_threshold=0.65
        )
        result = classifier.process(account_ticket)

        assert result.ai_used is True
        assert result.category == "account"
        assert result.assigned_team == "account-support"
