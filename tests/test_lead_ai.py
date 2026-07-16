from __future__ import annotations

import datetime as dt
import unittest
from pathlib import Path

from tests import support  # noqa: F401
from lead_ai import analyze_lead, extract_contact, load_scoring_policy, redact_sensitive_text, validate_provider_analysis


NOW = dt.datetime(2026, 7, 2, 12, tzinfo=dt.timezone.utc)


class StubProvider:
    last_message = ""
    def analyze(self, message: str) -> dict[str, object]:
        self.last_message = message
        return {
            "service_needed": "support_chatbot",
            "urgency": "medium",
            "budget_signal": "unknown",
            "intent": "high_intent",
            "ai_summary": "A bounded provider summary.",
            "suggested_reply": "A bounded provider reply.",
        }


class LeadAnalysisTests(unittest.TestCase):
    def test_hot_lead_is_scored_and_due_today(self) -> None:
        result = analyze_lead("Need appointment automation urgently. Budget is $1500.", NOW)
        self.assertEqual(result.priority_label, "Hot")
        self.assertEqual(result.follow_up_date, "2026-07-02")

    def test_unknown_service_uses_general_category(self) -> None:
        self.assertEqual(analyze_lead("Hello, please send information.", NOW).service_needed, "general_automation")

    def test_low_budget_is_detected(self) -> None:
        self.assertEqual(analyze_lead("Need a cheap CRM with a low budget.", NOW).budget_signal, "low_budget")

    def test_currency_amount_is_budget_signal(self) -> None:
        self.assertEqual(analyze_lead("Quote for reporting, 900 EUR.", NOW).budget_signal, "budget_mentioned")

    def test_research_language_is_medium_intent(self) -> None:
        self.assertEqual(analyze_lead("Just curious and researching chatbots.", NOW).intent, "medium_intent")

    def test_provider_output_is_used_and_rescored(self) -> None:
        provider=StubProvider(); result = analyze_lead("Unstructured inquiry", NOW, provider)
        self.assertEqual(result.analysis_mode, "openai")
        self.assertEqual(result.service_needed, "support_chatbot")
        self.assertEqual(result.ai_summary, "A bounded provider summary.")

    def test_provider_input_and_generated_fields_are_redacted(self):
        class PIIProvider(StubProvider):
            def analyze(self,message):
                self.last_message=message; result=super().analyze(message); result["ai_summary"]="Contact Alice at alice@example.com or +1 (212) 555-0199."; result["suggested_reply"]="Hi Alice, account 123456789012 is ready."; return result
        provider=PIIProvider(); result=analyze_lead("This is Alice from Acme Ltd. Need CRM urgently. Email alice@example.com or +1 (212) 555-0199.",NOW,provider)
        self.assertNotIn("Alice",provider.last_message); self.assertNotIn("alice@example.com",provider.last_message); self.assertNotIn("555-0199",provider.last_message); self.assertNotIn("alice@example.com",result.ai_summary); self.assertNotIn("555-0199",result.ai_summary); self.assertNotIn("Alice",result.suggested_reply); self.assertNotIn("123456789012",result.suggested_reply)

    def test_scoring_policy_is_external_and_validated(self):
        self.assertEqual(load_scoring_policy()["priority_thresholds"],{"hot":75,"warm":50})
        with self.assertRaisesRegex(ValueError,"readable JSON"): load_scoring_policy(Path("missing-policy.json"))

    def test_generic_redactor_preserves_budget_but_removes_account_number(self):
        value=redact_sensitive_text("Budget $1800, account 1234 5678 9012, email a@example.com"); self.assertIn("$1800",value); self.assertNotIn("1234 5678 9012",value); self.assertNotIn("a@example.com",value)

    def test_empty_message_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "required"):
            analyze_lead("   ", NOW)

    def test_provider_requires_exact_schema(self) -> None:
        with self.assertRaisesRegex(ValueError, "schema"):
            validate_provider_analysis({"urgency": "high"})

    def test_provider_rejects_unknown_enum(self) -> None:
        value = StubProvider().analyze("x")
        value["urgency"] = "emergency"
        with self.assertRaisesRegex(ValueError, "value"):
            validate_provider_analysis(value)

    def test_provider_rejects_oversized_text(self) -> None:
        value = StubProvider().analyze("x")
        value["ai_summary"] = "x" * 601
        with self.assertRaisesRegex(ValueError, "generated"):
            validate_provider_analysis(value)


class ContactExtractionTests(unittest.TestCase):
    def test_extracts_name_email_phone_and_company(self) -> None:
        result = extract_contact("This is Mark from BrightRoof. Email mark@example.com or +1 (212) 555-0199")
        self.assertEqual(result["name"], "Mark")
        self.assertEqual(result["company"], "BrightRoof")
        self.assertEqual(result["email"], "mark@example.com")
        self.assertEqual(result["phone"], "+1 (212) 555-0199")

    def test_does_not_accept_broken_email(self) -> None:
        self.assertEqual(extract_contact("write to name@example")["email"], "")

    def test_missing_contact_fields_are_empty(self) -> None:
        self.assertEqual(extract_contact("Need a dashboard"), {"name": "", "email": "", "phone": "", "company": ""})


if __name__ == "__main__":
    unittest.main()
