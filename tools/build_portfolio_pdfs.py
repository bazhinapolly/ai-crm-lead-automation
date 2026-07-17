"""Reproducibly build the two Upwork portfolio PDFs with ReportLab."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfgen.canvas import Canvas


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf"
NAVY = colors.HexColor("#132238")
TEAL = colors.HexColor("#087F5B")
BLUE = colors.HexColor("#2563EB")
PALE = colors.HexColor("#EFF8F5")
PALE_BLUE = colors.HexColor("#EEF4FF")
MUTED = colors.HexColor("#5F6F82")
LINE = colors.HexColor("#DCE5ED")


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "eyebrow": ParagraphStyle("eyebrow", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=11, tracking=1.2, textColor=TEAL, spaceAfter=7),
        "title": ParagraphStyle("title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=27, leading=30, alignment=TA_LEFT, textColor=NAVY, spaceAfter=9),
        "subtitle": ParagraphStyle("subtitle", parent=base["BodyText"], fontSize=11, leading=16, textColor=MUTED, spaceAfter=12),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=NAVY, spaceBefore=8, spaceAfter=6),
        "h3": ParagraphStyle("h3", parent=base["Heading3"], fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=TEAL, spaceAfter=3),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontSize=9.2, leading=13, textColor=NAVY, spaceAfter=5),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontSize=7.8, leading=10.5, textColor=MUTED),
        "bullet": ParagraphStyle("bullet", parent=base["BodyText"], fontSize=8.8, leading=12, leftIndent=11, firstLineIndent=-7, bulletIndent=0, textColor=NAVY, spaceAfter=3),
        "number": ParagraphStyle("number", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=18, leading=20, textColor=TEAL, alignment=TA_RIGHT),
        "table": ParagraphStyle("table", parent=base["BodyText"], fontSize=7.7, leading=10, textColor=NAVY),
        "table_head": ParagraphStyle("table_head", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=7.5, leading=9, textColor=colors.white),
        "code": ParagraphStyle("code", parent=base["BodyText"], fontName="Courier", fontSize=6.9, leading=9, textColor=colors.white),
    }


S = styles()


def p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, S[style])


def bullet(text: str) -> Paragraph:
    return Paragraph(f"- {text}", S["bullet"])


def page_frame(canvas, doc) -> None:  # type: ignore[no-untyped-def]
    canvas.saveState()
    width, height = LETTER
    canvas.setFillColor(TEAL)
    canvas.rect(0, height - 0.12 * inch, width, 0.12 * inch, stroke=0, fill=1)
    canvas.setStrokeColor(LINE)
    canvas.line(0.62 * inch, 0.48 * inch, width - 0.62 * inch, 0.48 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(0.62 * inch, 0.28 * inch, "AI CRM Lead Automation | Polina Bazhina | 2026")
    canvas.drawRightString(width - 0.62 * inch, 0.28 * inch, f"Page {doc.page}")
    canvas.restoreState()


def doc(path: Path, title: str) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        str(path),
        pagesize=LETTER,
        title=title,
        author="Polina Bazhina",
        subject="AI automation portfolio case study",
        leftMargin=0.62 * inch,
        rightMargin=0.62 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.62 * inch,
    )


def invariant_canvas(*args, **kwargs):
    kwargs["invariant"] = 1
    return Canvas(*args, **kwargs)


def summary_strip() -> Table:
    data = [
        [p("DELIVERY", "small"), p("ANALYSIS", "small"), p("QUALITY", "small"), p("DEPLOYMENT", "small")],
        [p("Local dashboard + API", "h3"), p("Offline or optional OpenAI", "h3"), p("76 automated tests", "h3"), p("Local-first application", "h3")],
    ]
    table = Table(data, colWidths=[1.68 * inch] * 4, rowHeights=[0.22 * inch, 0.42 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def build_case_study() -> None:
    path = OUTPUT / "AI-CRM-Lead-Automation-Case-Study.pdf"
    story = [
        p("PORTFOLIO CASE STUDY", "eyebrow"),
        p("AI CRM Lead Automation", "title"),
        p("A safe, testable workflow that converts inbound messages into structured CRM records, priorities, follow-up dates, and spreadsheet-safe exports.", "subtitle"),
        summary_strip(),
        Spacer(1, 0.13 * inch),
        p("The business problem", "h2"),
        p("Small teams receive inquiries through forms, inboxes, chat, and referrals. Manual interpretation and copy-paste work delay responses, lose context, and make it hard to see which lead needs attention first."),
        p("The implemented solution", "h2"),
        p("The local application validates each intake, extracts contact details, classifies the request, calculates a transparent Hot/Warm/Cold score, schedules follow-up, checks duplicate emails, and writes an audit event. A responsive dashboard, optionally authenticated loopback JSON endpoints, lifecycle controls, and CSV export make the result immediately reviewable."),
        p("Two analysis modes, one contract", "h2"),
        Table(
            [
                [p("DEFAULT: DETERMINISTIC", "table_head"), p("OPTIONAL: OPENAI", "table_head")],
                [p("Offline, repeatable, zero API cost. Versioned scoring policy feeds transparent priority and follow-up logic.", "table"), p("Best-effort redacted input, strict Structured Outputs, store: false, bounded retries, and local output redaction.", "table")],
            ],
            colWidths=[3.35 * inch, 3.35 * inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("BACKGROUND", (0, 1), (0, 1), PALE),
                ("BACKGROUND", (1, 1), (1, 1), PALE_BLUE),
                ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 9),
            ]),
        ),
        p("Workflow", "h2"),
        Table(
            [[p("1", "number"), p("Bounded JSON intake", "h3"), p("2", "number"), p("Contact + classification", "h3"), p("3", "number"), p("Atomic CRM write", "h3")],
             ["", p("Media type, byte count, object shape, source, and message length are validated.", "small"), "", p("Contacts are extracted locally; provider input and generated fields are redacted.", "small"), "", p("Lead, duplicate state, and event log commit in one versioned atomic state replacement.", "small")]],
            colWidths=[0.3 * inch, 1.92 * inch] * 3,
            style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEABOVE", (0, 0), (-1, 0), 0.8, LINE), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]),
        ),
        PageBreak(),
        p("ENGINEERING AND VERIFICATION", "eyebrow"),
        p("Built for credible review", "title"),
        p("An inspectable, production-oriented architecture with explicit privacy, security, and operating controls.", "subtitle"),
        Table(
            [
                [p("Reliable persistence", "h3"), p("Safer interfaces", "h3")],
                [[bullet("Transactional lead + event state"), bullet("OS-level interprocess file lock"), bullet("Atomic tempfile + replace commit"), bullet("Validated migration removes legacy PII files")], [bullet("Generic server errors"), bullet("HTML escaping and allowlisted classes"), bullet("Formula-safe CSV cells"), bullet("No-cache and browser security headers")]],
            ],
            colWidths=[3.35 * inch, 3.35 * inch],
            style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE), ("BOX", (0, 0), (-1, -1), 0.7, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 9)]),
        ),
        p("Privacy by default", "h2"),
        bullet("Raw inquiry text is not retained unless STORE_RAW_MESSAGE=1 is deliberately enabled."),
        bullet("API keys, provider bodies, and lead text are excluded from logs."),
        bullet("Detected contact fields are best-effort redacted before OpenAI; pattern-based anonymization is not guaranteed."),
        bullet("Optional bearer/session access includes TTL, logout, thread-safe login throttling, CSRF, deletion, and a 90-day purge policy."),
        bullet("Bounded intake and concurrent-provider controls return 429 with Retry-After."),
        bullet("Responses application-state storage is disabled with store: false."),
        p("Verification evidence", "h2"),
        Table(
            [[p("76", "number"), p("isolated tests", "h3"), p("6", "number"), p("simultaneous processes", "h3"), p("91", "number"), p("overall coverage (%)", "h3")],
             ["", p("PII, concurrency, lifecycle, auth, migration, CSV, HTML, and HTTP behavior.", "small"), "", p("Mandatory regression preserves all six leads and events in one shared state.", "small"), "", p("CI gate is 90%; storage 91%, app 88%, provider 97%.", "small")]],
            colWidths=[0.45 * inch, 1.78 * inch] * 3,
            style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE), ("BOX", (0, 0), (-1, -1), 0.7, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 7)]),
        ),
        p("Client adaptation path", "h2"),
        p("After requirements discovery, the same validated record can be connected to an authenticated form or inbox and written through one selected official CRM API. Production delivery makes authentication mandatory and adds authorization, TLS, distributed limits, a managed transactional database, scheduled lifecycle automation, monitoring, backups, and reconciliation."),
        p("Integration scope", "h2"),
        p("The JSON API and CSV export can serve as integration boundaries; platform-specific connectors are not implemented. A client adaptation selects one official API and adds credentials, mapping, idempotency, and reconciliation. No client deployment, client acceptance, live model-quality score, or measured business outcome is claimed."),
        p("Verified locally 2026-07-17 | release v2.1.0 | 76 tests | github.com/bazhinapolly/ai-crm-lead-automation", "small"),
    ]
    doc(path, "AI CRM Lead Automation - Case Study").build(story, onFirstPage=page_frame, onLaterPages=page_frame, canvasmaker=invariant_canvas)


def build_technical_summary() -> None:
    path = OUTPUT / "AI-CRM-Lead-Automation-Technical-Summary.pdf"
    endpoints = [
        [p("METHOD", "table_head"), p("ROUTE", "table_head"), p("PURPOSE", "table_head")],
        [p("GET", "table"), p("/ and /api/health", "table"), p("Dashboard and mode-aware health check", "table")],
        [p("POST", "table"), p("/api/intake", "table"), p("Validate, classify, score, and persist one lead", "table")],
        [p("GET", "table"), p("/api/leads and /api/logs", "table"), p("Structured CRM records, metrics, and audit events", "table")],
        [p("GET/DELETE", "table"), p("/api/leads/{id}", "table"), p("Export or delete one contact record", "table")],
        [p("POST", "table"), p("/api/maintenance/purge", "table"), p("Apply configured contact retention", "table")],
        [p("GET", "table"), p("/export/leads.csv", "table"), p("Formula-neutralized spreadsheet handoff", "table")],
    ]
    story = [
        p("TECHNICAL SUMMARY", "eyebrow"),
        p("AI CRM Lead Automation", "title"),
        p("Python 3.11+ local application | Standard-library runtime | Optional OpenAI Responses API | MIT licensed", "subtitle"),
        summary_strip(),
        p("Architecture", "h2"),
        Table(
            [[p("INTAKE", "table_head"), p("ANALYSIS", "table_head"), p("PERSISTENCE", "table_head"), p("DELIVERY", "table_head")],
            [p("Threaded local HTTP server, request bounds, optional bearer/session access, CSRF, intake limits.", "table"), p("Versioned scoring policy or redacted Structured Outputs; provider concurrency cap.", "table"), p("OS interprocess file lock, atomic state, validated legacy cleanup, retention, export/delete.", "table"), p("Escaped dashboard, JSON endpoints, date-accurate metrics, event log, formula-safe CSV.", "table")]],
            colWidths=[1.675 * inch] * 4,
            style=TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("BACKGROUND", (0, 1), (-1, 1), PALE), ("BOX", (0, 0), (-1, -1), 0.7, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 7)]),
        ),
        p("HTTP surface", "h2"),
        Table(endpoints, colWidths=[0.95 * inch, 1.95 * inch, 3.8 * inch], repeatRows=1, style=TableStyle([("BACKGROUND", (0, 0), (-1, 0), TEAL), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]), ("BOX", (0, 0), (-1, -1), 0.7, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 6)])),
        p("Security and privacy controls", "h2"),
        Table(
            [[[bullet("Loopback-only host validation"), bullet("TTL sessions, logout, login throttling"), bullet("Browser CSRF protection"), bullet("Security and no-cache headers")], [bullet("CSV formula neutralization"), bullet("Legacy PII files removed after migration"), bullet("Invalid timestamps fail safely"), bullet("90-day purge plus export/delete by ID")]]],
            colWidths=[3.35 * inch, 3.35 * inch],
            style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE), ("BOX", (0, 0), (-1, -1), 0.7, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 7)]),
        ),
        p("Verification", "h2"),
        p("76 isolated tests cover configuration, email extraction/redaction, provider output, intake/provider limits, concurrent sessions/login throttling, interprocess storage, atomic migration, retention, CSRF, CSV/HTML safety, and local HTTP behavior. Six-process regression evidence and 91% overall coverage run in CI on Python 3.11-3.13."),
        p("Run locally", "h2"),
        Table([[p("python3 -m unittest discover -s tests -v", "code"), p("python3 src/seed_data.py --reset", "code"), p("python3 src/app.py", "code")]], colWidths=[2.6 * inch, 2.05 * inch, 2.05 * inch], style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY), ("BOX", (0, 0), (-1, -1), 0.7, NAVY), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("PADDING", (0, 0), (-1, -1), 7)])),
        Spacer(1, 0.04 * inch),
        p("Verified locally 2026-07-17 | release v2.1.0 | 76 tests | github.com/bazhinapolly/ai-crm-lead-automation<br/>No client deployment or measured business outcome claimed. Production rollout requires mandatory identity/authorization, TLS, managed persistence, distributed controls, monitoring, backups, and scheduled lifecycle controls.", "small"),
    ]
    doc(path, "AI CRM Lead Automation - Technical Summary").build(story, onFirstPage=page_frame, onLaterPages=page_frame, canvasmaker=invariant_canvas)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    build_case_study()
    build_technical_summary()
    for path in sorted(OUTPUT.glob("*.pdf")):
        print(f"Built {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
