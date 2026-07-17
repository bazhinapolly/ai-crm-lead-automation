from __future__ import annotations

import http.client
import json
import re
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from tests import support  # noqa: F401
from app import make_handler, render_lead_row, render_login, validate_intake
from config import Settings
from openai_provider import OpenAIProviderError
from storage import DataStoreError, JsonCRM


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

    def test_read_routes_and_login_page_are_available_in_local_mode(self) -> None:
        self.store.create_lead("form", "Need CRM")
        self.assertEqual(self.request("GET", "/login")[0], 200)
        self.assertEqual(self.request("GET", "/api/logs")[0], 200)
        status, headers, body = self.request("GET", "/export/leads.csv")
        self.assertEqual(status, 200)
        self.assertIn("attachment", headers["Content-Disposition"])
        self.assertIn(b"suggested_reply", body)
        self.assertEqual(self.request("POST", "/unknown")[0], 404)
        self.assertEqual(self.request("POST", "/auth/login", b"api_key=x")[0], 404)

    def test_unsupported_method_is_405(self) -> None:
        status, headers, _ = self.request("DELETE", "/api/leads")
        self.assertEqual(status, 405)
        self.assertEqual(headers["Allow"], "GET, POST")

    def test_invalid_source_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "source"):
            validate_intake({"source": "<script>", "message": "hello"}, 100)
        with self.assertRaisesRegex(ValueError, "non-empty"):
            validate_intake({"message": " "}, 100)
        with self.assertRaisesRegex(ValueError, "at most"):
            validate_intake({"message": "x" * 101}, 100)

    def test_dashboard_escapes_stored_values_and_class_name(self) -> None:
        row = render_lead_row({"name": "<img>", "priority_label": 'Hot onclick="bad"', "priority_score": 3})
        self.assertNotIn("<img>", row)
        self.assertNotIn("onclick=", row.split("class='badge", 1)[1].split("'", 1)[0])

    def test_lead_export_delete_and_purge_endpoints(self) -> None:
        lead = self.store.create_lead("form", "Need CRM. Email lead@example.com")
        status, _, body = self.request("GET", f"/api/leads/{lead['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["lead"]["email"], "lead@example.com")
        self.assertEqual(self.request("GET", "/api/leads/missing")[0], 404)
        status, _, body = self.request("DELETE", f"/api/leads/{lead['id']}")
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["deleted"])
        status, _, body = self.request("POST", "/api/maintenance/purge")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["purged_ids"], [])

    def test_browser_requests_require_csrf_token(self) -> None:
        body = json.dumps({"source": "form", "message": "Need CRM"}).encode()
        status, _, response = self.request(
            "POST",
            "/api/intake",
            body,
            {"Content-Type": "application/json", "Origin": "http://127.0.0.1"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(response)["error"], "csrf_failed")
        _, _, dashboard = self.request("GET", "/")
        token = re.search(rb"const csrf=\"([^\"]+)\"", dashboard).group(1).decode()
        status, _, _ = self.request(
            "POST",
            "/api/intake",
            body,
            {"Content-Type": "application/json", "Origin": "http://127.0.0.1", "X-CSRF-Token": token},
        )
        self.assertEqual(status, 201)

    def test_optional_local_key_supports_bearer_and_browser_session_auth(self) -> None:
        key = "k" * 32
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            make_handler(self.store, Settings(data_dir=Path(self.temporary.name), local_api_key=key)),
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def secured_request(method, path, body=None, headers=None):
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            result = response.status, dict(response.getheaders()), response.read()
            connection.close()
            return result

        try:
            self.assertEqual(secured_request("GET", "/api/leads")[0], 401)
            self.assertEqual(secured_request("GET", "/")[0], 303)
            self.assertEqual(secured_request("GET", "/api/leads", headers={"Authorization": f"Bearer {key}"})[0], 200)
            self.assertEqual(secured_request("POST", "/api/intake", b"{}", {"Content-Type": "application/json"})[0], 401)
            self.assertEqual(secured_request("DELETE", "/api/leads/missing")[0], 401)

            wrong = secured_request("POST", "/auth/login", b"api_key=wrong", {"Content-Type": "application/x-www-form-urlencoded"})
            self.assertEqual(wrong[0], 401)
            self.assertIn(b"Invalid local access key", wrong[2])

            login_body = f"api_key={key}".encode()
            status, headers, _ = secured_request(
                "POST", "/auth/login", login_body, {"Content-Type": "application/x-www-form-urlencoded"}
            )
            self.assertEqual(status, 303)
            cookie = headers["Set-Cookie"].split(";", 1)[0]
            status, _, dashboard = secured_request("GET", "/", headers={"Cookie": cookie})
            self.assertEqual(status, 200)
            csrf = re.search(rb"const csrf=\"([^\"]+)\"", dashboard).group(1).decode()
            intake = json.dumps({"source": "form", "message": "Need a dashboard"}).encode()
            self.assertEqual(secured_request("POST", "/api/intake", intake, {"Cookie": cookie, "Content-Type": "application/json"})[0], 403)
            self.assertEqual(secured_request("POST", "/api/intake", intake, {"Cookie": cookie, "Content-Type": "application/json", "X-CSRF-Token": csrf})[0], 201)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_login_renderer_escapes_notice(self) -> None:
        self.assertNotIn("<script>", render_login("<script>"))

    def test_safe_http_errors_cover_provider_storage_and_unexpected_failures(self) -> None:
        payload = json.dumps({"source": "form", "message": "Need CRM"}).encode()
        headers = {"Content-Type": "application/json"}
        with patch("app.LOGGER.exception"):
            for failure, expected in (
                (OpenAIProviderError("private"), (502, "analysis_unavailable")),
                (DataStoreError("private"), (500, "storage_unavailable")),
                (RuntimeError("private"), (500, "server_error")),
            ):
                with self.subTest(failure=type(failure).__name__), patch.object(self.store, "create_lead", side_effect=failure):
                    status, _, body = self.request("POST", "/api/intake", payload, headers)
                    self.assertEqual((status, json.loads(body)["error"]), expected)
            with patch.object(self.store, "list_logs", side_effect=DataStoreError("private")):
                status, _, body = self.request("GET", "/api/logs")
                self.assertEqual(status, 500)
                self.assertEqual(json.loads(body)["error"], "storage_unavailable")


if __name__ == "__main__":
    unittest.main()
