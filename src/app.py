"""Local demo web app for the AI CRM Lead Automation System."""

from __future__ import annotations

import json
import os
import errno
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from storage import create_lead, export_leads_csv, list_leads, list_logs, pipeline_metrics


HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "8080"))


class CRMHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/":
            self.send_html(render_dashboard())
        elif route == "/api/health":
            self.send_json({"ok": True, "service": "ai-crm-lead-automation"})
        elif route == "/api/leads":
            self.send_json({"leads": list_leads(), "metrics": pipeline_metrics()})
        elif route == "/api/logs":
            self.send_json({"logs": list_logs()})
        elif route == "/export/leads.csv":
            self.send_csv(export_leads_csv())
        else:
            self.send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        if route != "/api/intake":
            self.send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            return

        try:
            payload = self.read_json()
            lead = create_lead(payload.get("source", "manual"), payload.get("message", ""))
            self.send_json({"lead": lead}, HTTPStatus.CREATED)
        except ValueError as error:
            self.send_json({"error": "invalid_request", "message": str(error)}, HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self.send_json({"error": "invalid_json"}, HTTPStatus.BAD_REQUEST)
        except Exception as error:  # Demo safety net for portfolio verification.
            self.send_json(
                {"error": "server_error", "message": str(error)},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        return json.loads(body or "{}")

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_csv(self, csv_text: str) -> None:
        body = csv_text.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", "attachment; filename=leads.csv")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return


def render_dashboard() -> str:
    leads = list_leads()
    metrics = pipeline_metrics()
    rows = "\n".join(render_lead_row(lead) for lead in leads)
    sample_message = (
        "Hi, this is Olivia from Peak Home Services. We need a CRM automation "
        "that captures quote requests, scores urgent leads, and reminds our team "
        "to follow up. Budget is around $1800. Email olivia@peakhome.example."
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI CRM Lead Automation</title>
  <style>
    :root {{
      --ink: #17202a;
      --muted: #607084;
      --line: #d9e2ec;
      --bg: #f6f8fb;
      --card: #ffffff;
      --hot: #c2410c;
      --warm: #b7791f;
      --cold: #2b6cb0;
      --green: #047857;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: radial-gradient(circle at top left, #e8fff4, transparent 34%),
                  linear-gradient(135deg, #f9fbff 0%, #eef4f8 100%);
    }}
    header {{
      padding: 44px min(6vw, 72px) 24px;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(36px, 6vw, 68px);
      line-height: 0.95;
      letter-spacing: -0.05em;
    }}
    .subtitle {{
      margin-top: 16px;
      max-width: 820px;
      color: var(--muted);
      font-size: 18px;
      line-height: 1.6;
    }}
    main {{ padding: 0 min(6vw, 72px) 56px; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(5, minmax(150px, 1fr));
      gap: 16px;
      margin: 24px 0;
    }}
    .metric, .panel {{
      background: rgba(255,255,255,0.82);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: 0 16px 40px rgba(31, 41, 55, 0.08);
    }}
    .metric {{ padding: 18px; }}
    .metric strong {{ display:block; font-size: 32px; }}
    .metric span {{ color: var(--muted); font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .grid {{
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 18px;
      align-items: start;
    }}
    .panel {{ padding: 22px; overflow: hidden; }}
    .panel h2 {{ margin: 0 0 16px; font-size: 22px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ padding: 12px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .badge {{
      display: inline-flex;
      padding: 5px 9px;
      border-radius: 999px;
      color: #fff;
      font-size: 12px;
      font-weight: 700;
    }}
    .Hot {{ background: var(--hot); }}
    .Warm {{ background: var(--warm); }}
    .Cold {{ background: var(--cold); }}
    textarea, input {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px 14px;
      font: inherit;
      background: #fff;
    }}
    textarea {{ min-height: 150px; resize: vertical; }}
    label {{ display: block; margin: 12px 0 6px; color: var(--muted); font-size: 13px; font-weight: 700; }}
    button, .button {{
      border: 0;
      border-radius: 14px;
      padding: 12px 16px;
      background: var(--green);
      color: #fff;
      font-weight: 800;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      margin-top: 12px;
    }}
    .button.secondary {{ background: #243447; margin-left: 8px; }}
    .summary {{ color: var(--muted); max-width: 360px; }}
    @media (max-width: 980px) {{
      .metrics, .grid {{ grid-template-columns: 1fr; }}
      table {{ min-width: 760px; }}
      .table-wrap {{ overflow-x: auto; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>AI CRM Lead Automation</h1>
    <p class="subtitle">
      Demo operations hub for service businesses: capture inbound leads, extract key details,
      score urgency and intent, generate follow-up actions, and keep a lightweight CRM dashboard.
    </p>
  </header>
  <main>
    <section class="metrics">
      <div class="metric"><strong>{metrics["total_leads"]}</strong><span>Total leads</span></div>
      <div class="metric"><strong>{metrics["hot_leads"]}</strong><span>Hot</span></div>
      <div class="metric"><strong>{metrics["warm_leads"]}</strong><span>Warm</span></div>
      <div class="metric"><strong>{metrics["follow_up_today"]}</strong><span>Follow up today</span></div>
      <div class="metric"><strong>{metrics["average_score"]}</strong><span>Avg score</span></div>
    </section>
    <section class="grid">
      <div class="panel">
        <h2>CRM Pipeline</h2>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Lead</th>
                <th>Service</th>
                <th>Priority</th>
                <th>Stage</th>
                <th>Follow-up</th>
                <th>AI Summary</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
        <a class="button secondary" href="/export/leads.csv">Export CSV</a>
      </div>
      <div class="panel">
        <h2>Submit Demo Lead</h2>
        <p class="summary">Paste a lead email, form submission, or chat message. The demo will extract CRM fields and score it automatically.</p>
        <label for="source">Source</label>
        <input id="source" value="website_form">
        <label for="message">Message</label>
        <textarea id="message">{sample_message}</textarea>
        <button onclick="submitLead()">Analyze and Add Lead</button>
        <p id="result" class="summary"></p>
      </div>
    </section>
  </main>
  <script>
    async function submitLead() {{
      const result = document.getElementById('result');
      result.textContent = 'Processing...';
      const response = await fetch('/api/intake', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
          source: document.getElementById('source').value,
          message: document.getElementById('message').value
        }})
      }});
      const data = await response.json();
      if (!response.ok) {{
        result.textContent = data.message || data.error || 'Request failed';
        return;
      }}
      result.textContent = `Created ${{data.lead.priority_label}} lead: ${{data.lead.next_action}}`;
      setTimeout(() => location.reload(), 900);
    }}
  </script>
</body>
</html>"""


def render_lead_row(lead: dict) -> str:
    lead_name = lead.get("name") or lead.get("company") or lead.get("email") or "Unknown lead"
    return f"""
      <tr>
        <td><strong>{escape(lead_name)}</strong><br><span class="summary">{escape(lead.get("email", ""))}</span></td>
        <td>{escape(lead.get("service_needed", ""))}</td>
        <td><span class="badge {lead.get("priority_label", "Cold")}">{escape(lead.get("priority_label", ""))} · {lead.get("priority_score", "")}</span></td>
        <td>{escape(lead.get("pipeline_stage", ""))}</td>
        <td>{escape(lead.get("follow_up_date", ""))}</td>
        <td class="summary">{escape(lead.get("ai_summary", ""))}</td>
      </tr>
    """


def escape(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def main() -> None:
    try:
        server = ThreadingHTTPServer((HOST, PORT), CRMHandler)
    except OSError as error:
        if error.errno == errno.EADDRINUSE:
            print(
                f"Port {PORT} is already in use. Try another port, for example: "
                "PORT=8090 python3 src/app.py"
            )
            return
        raise
    print(f"AI CRM Lead Automation demo running at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
