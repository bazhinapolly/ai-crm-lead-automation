from __future__ import annotations

import http.client
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from tests import support  # noqa: F401
from app import make_handler, render_lead_row, validate_intake
from config import Settings
from storage import JsonCRM


class AppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.store = JsonCRM(Path(self.temporary.name))
        self.settings = Settings(data_dir=Path(self.temporary.name), max_request_bytes=512)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.store, self.settings))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temporary.cleanup()

    def request(self, method: str, path: str, body: bytes | None = None, headers: dict[str, str] | None = None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        data = response.read()
        result = (response.status, dict(response.getheaders()), data)
        connection.close()
        return result

    def test_health_reports_mode_and_security_headers(self) -> None:
        status, headers, body = self.request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["mode"], "deterministic")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_intake_creates_lead(self) -> None:
        body = json.dumps({"source": "website_form", "message": "Need CRM ASAP"}).encode()
        status, _, data = self.request("POST", "/api/intake", body, {"Content-Type": "application/json"})
        self.assertEqual(status, 201)
        self.assertEqual(json.loads(data)["lead"]["source"], "website_form")

    def test_wrong_content_type_is_rejected(self) -> None:
        status, _, body = self.request("POST", "/api/intake", b"{}", {"Content-Type": "text/plain"})
        self.assertEqual(status, 415)
        self.assertEqual(json.loads(body)["error"], "unsupported_media_type")

    def test_invalid_utf8_is_rejected(self) -> None:
        status, _, body = self.request("POST", "/api/intake", b"\xff", {"Content-Type": "application/json"})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["error"], "invalid_json")

    def test_array_payload_is_rejected(self) -> None:
        status, _, body = self.request("POST", "/api/intake", b"[]", {"Content-Type": "application/json"})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["error"], "invalid_request")

    def test_oversized_body_is_rejected_before_read(self) -> None:
        status, _, body = self.request("POST", "/api/intake", b"x" * 513, {"Content-Type": "application/json"})
        self.assertEqual(status, 413)
        self.assertEqual(json.loads(body)["error"], "request_too_large")

    def test_unknown_route_is_404(self) -> None:
        self.assertEqual(self.request("GET", "/unknown")[0], 404)

    def test_unsupported_method_is_405(self) -> None:
        status, headers, _ = self.request("DELETE", "/api/leads")
        self.assertEqual(status, 405)
        self.assertEqual(headers["Allow"], "GET, POST")

    def test_invalid_source_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "source"):
            validate_intake({"source": "<script>", "message": "hello"}, 100)

    def test_dashboard_escapes_stored_values_and_class_name(self) -> None:
        row = render_lead_row({"name": "<img>", "priority_label": 'Hot onclick="bad"', "priority_score": 3})
        self.assertNotIn("<img>", row)
        self.assertNotIn("onclick=", row.split("class='badge", 1)[1].split("'", 1)[0])


if __name__ == "__main__":
    unittest.main()
