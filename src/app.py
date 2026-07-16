"""Local HTTP dashboard and JSON API for CRM lead automation."""

from __future__ import annotations

import errno
import html
import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from config import Settings
from openai_provider import OpenAIProvider, OpenAIProviderError
from storage import DataStoreError, JsonCRM


LOGGER = logging.getLogger(__name__)
SOURCE_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-")


def validate_intake(payload: object, max_message_chars: int) -> tuple[str, str]:
    if not isinstance(payload, dict):
        raise ValueError("JSON body must be an object")
    source = payload.get("source", "manual")
    message = payload.get("message")
    if not isinstance(source, str) or not 1 <= len(source) <= 80 or any(char not in SOURCE_CHARS for char in source):
        raise ValueError("source must be 1-80 letters, numbers, dots, colons, underscores, or hyphens")
    if not isinstance(message, str) or not message.strip():
        raise ValueError("message must be a non-empty string")
    message = " ".join(message.split())
    if len(message) > max_message_chars:
        raise ValueError(f"message must be at most {max_message_chars} characters")
    return source, message


def make_handler(store: JsonCRM, settings: Settings) -> type[BaseHTTPRequestHandler]:
    class CRMHandler(BaseHTTPRequestHandler):
        server_version = "CRMReference/1.0"
        sys_version = ""

        def do_GET(self) -> None:  # noqa: N802
            route = urlparse(self.path).path
            try:
                if route == "/":
                    self._send(render_dashboard(store), "text/html; charset=utf-8")
                elif route == "/api/health":
                    self.send_json({"ok": True, "service": "ai-crm-lead-automation", "mode": "openai" if settings.use_openai else "deterministic"})
                elif route == "/api/leads":
                    self.send_json({"leads": store.list_leads(), "metrics": store.pipeline_metrics()})
                elif route == "/api/logs":
                    self.send_json({"logs": store.list_logs()})
                elif route == "/export/leads.csv":
                    self._send(
                        store.export_leads_csv(),
                        "text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="leads.csv"'},
                    )
                else:
                    self.send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            except DataStoreError:
                LOGGER.exception("CRM data could not be read")
                self.send_json({"error": "storage_unavailable"}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def do_POST(self) -> None:  # noqa: N802
            if urlparse(self.path).path != "/api/intake":
                self.send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
                return
            try:
                source, message = validate_intake(self.read_json(), settings.max_message_chars)
                self.send_json({"lead": store.create_lead(source, message)}, HTTPStatus.CREATED)
            except RequestError as error:
                self.send_json({"error": error.code}, error.status)
            except ValueError as error:
                self.send_json({"error": "invalid_request", "message": str(error)}, HTTPStatus.BAD_REQUEST)
            except OpenAIProviderError:
                self.send_json({"error": "analysis_unavailable"}, HTTPStatus.BAD_GATEWAY)
            except DataStoreError:
                LOGGER.exception("CRM data could not be written")
                self.send_json({"error": "storage_unavailable"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            except Exception:
                LOGGER.exception("Unexpected intake failure")
                self.send_json({"error": "server_error"}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_json({"error": "method_not_allowed"}, HTTPStatus.METHOD_NOT_ALLOWED, {"Allow": "GET, POST"})

        do_PUT = do_OPTIONS
        do_PATCH = do_OPTIONS
        do_DELETE = do_OPTIONS
        do_HEAD = do_OPTIONS

        def read_json(self) -> object:
            media_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if media_type != "application/json":
                raise RequestError("unsupported_media_type", HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                raise RequestError("length_required", HTTPStatus.LENGTH_REQUIRED)
            try:
                length = int(raw_length)
            except ValueError as exc:
                raise RequestError("invalid_content_length", HTTPStatus.BAD_REQUEST) from exc
            if length < 0:
                raise RequestError("invalid_content_length", HTTPStatus.BAD_REQUEST)
            if length > settings.max_request_bytes:
                raise RequestError("request_too_large", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            try:
                return json.loads(self.rfile.read(length).decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise RequestError("invalid_json", HTTPStatus.BAD_REQUEST) from exc

        def send_json(
            self,
            payload: dict[str, Any],
            status: HTTPStatus = HTTPStatus.OK,
            headers: dict[str, str] | None = None,
        ) -> None:
            self._send(json.dumps(payload, ensure_ascii=False), "application/json; charset=utf-8", status, headers)

        def _send(
            self,
            value: str,
            content_type: str,
            status: HTTPStatus = HTTPStatus.OK,
            headers: dict[str, str] | None = None,
        ) -> None:
            body = value.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'")
            for key, item in (headers or {}).items():
                self.send_header(key, item)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            LOGGER.info("%s - %s", self.address_string(), format % args)

    return CRMHandler


class RequestError(Exception):
    def __init__(self, code: str, status: HTTPStatus) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


def render_dashboard(store: JsonCRM) -> str:
    metrics = store.pipeline_metrics()
    rows = "".join(render_lead_row(lead) for lead in store.list_leads()) or '<tr><td colspan="6" class="empty">No leads yet. Submit the sample to begin.</td></tr>'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI CRM Lead Automation</title><style>
:root{{--ink:#132238;--muted:#65758b;--line:#dbe4ee;--paper:#fff;--accent:#087f5b;--navy:#1d3557;--hot:#c2410c;--warm:#a16207;--cold:#2563eb}}
*{{box-sizing:border-box}}body{{margin:0;background:linear-gradient(145deg,#f6fbfa,#edf3f9);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,sans-serif}}
header,main{{width:min(1180px,92vw);margin:auto}}header{{padding:54px 0 22px}}.eyebrow{{color:var(--accent);font-weight:800;letter-spacing:.13em;text-transform:uppercase;font-size:12px}}
h1{{font-size:clamp(38px,6vw,70px);line-height:.98;letter-spacing:-.05em;margin:10px 0 16px;max-width:850px}}.intro{{max-width:760px;color:var(--muted);line-height:1.7;font-size:17px}}
.metrics{{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin:24px 0}}.card,.panel{{background:rgba(255,255,255,.9);border:1px solid var(--line);border-radius:20px;box-shadow:0 16px 45px rgba(30,53,80,.08)}}
.card{{padding:18px}}.card strong{{font-size:30px;display:block}}.card span{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}}.layout{{display:grid;grid-template-columns:1.3fr .7fr;gap:16px;padding-bottom:50px}}.panel{{padding:22px;overflow:hidden}}h2{{margin:0 0 14px}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{padding:11px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}th{{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}}
.badge{{display:inline-block;color:#fff;border-radius:999px;padding:5px 9px;font-weight:800}}.Hot{{background:var(--hot)}}.Warm{{background:var(--warm)}}.Cold{{background:var(--cold)}}.muted,.empty{{color:var(--muted)}}label{{display:block;font-size:12px;font-weight:800;color:var(--muted);margin:12px 0 6px}}input,textarea{{width:100%;font:inherit;padding:12px;border:1px solid var(--line);border-radius:12px}}textarea{{min-height:170px;resize:vertical}}button,.button{{display:inline-block;margin-top:12px;border:0;border-radius:12px;padding:12px 15px;background:var(--accent);color:#fff;text-decoration:none;font-weight:800;cursor:pointer}}.button{{background:var(--navy)}}#result{{min-height:24px}}@media(max-width:900px){{.metrics,.layout{{grid-template-columns:1fr 1fr}}.pipeline{{grid-column:1/-1}}.scroll{{overflow:auto}}table{{min-width:760px}}}}@media(max-width:560px){{.metrics,.layout{{grid-template-columns:1fr}}}}
</style></head><body><header><div class="eyebrow">Local CRM application</div><h1>Turn inbound messages into an actionable CRM queue.</h1><p class="intro">Structured intake, deterministic or optional AI analysis, duplicate detection, safe local storage, follow-up priorities, and CSV handoff.</p></header>
<main><section class="metrics">{metric("Total", metrics["total_leads"])}{metric("Hot", metrics["hot_leads"])}{metric("Warm", metrics["warm_leads"])}{metric("Today", metrics["follow_up_today"])}{metric("Avg score", metrics["average_score"])}</section>
<section class="layout"><div class="panel pipeline"><h2>Lead pipeline</h2><div class="scroll"><table><thead><tr><th>Lead</th><th>Service</th><th>Priority</th><th>Stage</th><th>Follow-up</th><th>Summary</th></tr></thead><tbody>{rows}</tbody></table></div><a class="button" href="/export/leads.csv">Export safe CSV</a></div>
<div class="panel"><h2>Submit a lead</h2><p class="muted">The default mode is deterministic and makes no external request.</p><label for="source">Source</label><input id="source" value="website_form" maxlength="80"><label for="message">Message</label><textarea id="message" maxlength="10000">Hi, this is Olivia from Peak Home Services. We need CRM automation urgently. Budget is $1800. Email olivia@peakhome.example.</textarea><button id="submit">Analyze and add</button><p id="result" class="muted" aria-live="polite"></p></div></section></main>
<script>document.getElementById('submit').addEventListener('click',async()=>{{const r=document.getElementById('result');r.textContent='Processing...';try{{const response=await fetch('/api/intake',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{source:document.getElementById('source').value,message:document.getElementById('message').value}})}});const data=await response.json();if(!response.ok)throw new Error(data.message||data.error||'Request failed');r.textContent=`Created ${{data.lead.priority_label}} lead. ${{data.lead.next_action}}`;setTimeout(()=>location.reload(),700)}}catch(error){{r.textContent=error.message}}}});</script></body></html>"""


def metric(label: str, value: object) -> str:
    return f'<div class="card"><strong>{html.escape(str(value))}</strong><span>{html.escape(label)}</span></div>'


def render_lead_row(lead: dict[str, object]) -> str:
    label = str(lead.get("priority_label", "Cold"))
    css_label = label if label in {"Hot", "Warm", "Cold"} else "Cold"
    display_name = lead.get("name") or lead.get("company") or lead.get("email") or "Unknown lead"
    esc = lambda value: html.escape(str(value), quote=True)
    return (
        f"<tr><td><strong>{esc(display_name)}</strong><br><span class='muted'>{esc(lead.get('email', ''))}</span></td>"
        f"<td>{esc(lead.get('service_needed', ''))}</td><td><span class='badge {css_label}'>{esc(label)} - {esc(lead.get('priority_score', ''))}</span></td>"
        f"<td>{esc(lead.get('pipeline_stage', ''))}</td><td>{esc(lead.get('follow_up_date', ''))}</td><td class='muted'>{esc(lead.get('ai_summary', ''))}</td></tr>"
    )


def build_store(settings: Settings) -> JsonCRM:
    provider = OpenAIProvider(settings.openai_api_key, settings.openai_model, settings.openai_timeout_seconds) if settings.use_openai else None
    return JsonCRM(settings.data_dir, provider=provider, store_raw_message=settings.store_raw_message)


def build_server(settings: Settings) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((settings.host, settings.port), make_handler(build_store(settings), settings))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        settings = Settings.from_env()
        server = build_server(settings)
    except ValueError as error:
        raise SystemExit(f"Configuration error: {error}") from error
    except OSError as error:
        if error.errno == errno.EADDRINUSE:
            raise SystemExit(f"Port is in use. Try: PORT=8090 python3 src/app.py") from error
        raise
    print(f"CRM application running at http://{settings.host}:{settings.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
