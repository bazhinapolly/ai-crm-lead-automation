from __future__ import annotations

import io
import json
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from tests import support  # noqa: F401
from openai_provider import OpenAIProvider, OpenAIProviderError


VALID = {
    "service_needed": "crm_automation",
    "urgency": "high",
    "budget_signal": "budget_mentioned",
    "intent": "high_intent",
    "ai_summary": "Qualified CRM inquiry.",
    "suggested_reply": "Let's schedule a discovery call.",
}


class Response:
    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.headers = {"x-request-id": "req_test"}

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


class OpenAIProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = OpenAIProvider("secret", "model-test", max_attempts=2)

    def test_payload_disables_storage_and_uses_strict_schema(self) -> None:
        payload = self.provider._payload("message")
        self.assertIs(payload["store"], False)
        self.assertTrue(payload["text"]["format"]["strict"])
        self.assertEqual(payload["model"], "model-test")

    @patch("openai_provider.urllib.request.urlopen")
    def test_parses_structured_output(self, urlopen: MagicMock) -> None:
        urlopen.return_value = Response({"status": "completed", "output": [{"content": [{"type": "output_text", "text": json.dumps(VALID)}]}]})
        self.assertEqual(self.provider.analyze("lead"), VALID)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer secret")
        invalid = dict(VALID, urgency="emergency")
        urlopen.return_value = Response({"status": "completed", "output": [{"content": [{"type": "output_text", "text": json.dumps(invalid)}]}]})
        with self.assertRaisesRegex(OpenAIProviderError, "invalid structured output"):
            self.provider.analyze("lead")

    def test_refusal_is_safe_failure(self) -> None:
        with self.assertRaisesRegex(OpenAIProviderError, "refused"):
            self.provider._extract_output({"output": [{"content": [{"type": "refusal"}]}]})

    def test_incomplete_result_is_safe_failure(self) -> None:
        with self.assertRaisesRegex(OpenAIProviderError, "complete"):
            self.provider._extract_output({"status": "incomplete"})

    @patch("openai_provider.time.sleep")
    @patch("openai_provider.urllib.request.urlopen")
    def test_transient_error_is_retried(self, urlopen: MagicMock, sleep: MagicMock) -> None:
        failure = urllib.error.HTTPError("url", 429, "rate", {"x-request-id": "req_429"}, io.BytesIO())
        success = Response({"status": "completed", "output": [{"content": [{"type": "output_text", "text": json.dumps(VALID)}]}]})
        urlopen.side_effect = [failure, success]
        self.assertEqual(self.provider.analyze("lead"), VALID)
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once()

    @patch("openai_provider.urllib.request.urlopen")
    def test_non_retryable_error_is_redacted(self, urlopen: MagicMock) -> None:
        urlopen.side_effect = urllib.error.HTTPError("url", 401, "bad", {}, io.BytesIO(b"sensitive body"))
        with self.assertRaisesRegex(OpenAIProviderError, "temporarily unavailable") as caught:
            self.provider.analyze("private lead")
        self.assertNotIn("sensitive", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
