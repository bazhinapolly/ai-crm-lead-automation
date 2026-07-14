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


def summary_strip() -> Table:
    data = [
        [p("DELIVERY", "small"), p("ANALYSIS", "small"), p("QUALITY", "small"), p("BOUNDARY", "small")],
        [p("Local dashboard + API", "h3"), p("Offline or optional OpenAI", "h3"), p("39 automated tests", "h3"), p("Reference app, not SaaS", "h3")],
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
        p("The local application validates each intake, extracts contact details, classifies the request, calculates a transparent Hot/Warm/Cold score, schedules follow-up, checks duplicate emails, and writes an audit event. A responsive dashboard, JSON endpoints, and CSV export make the result immediately reviewable."),
        p("Two analysis modes, one contract", "h2"),
        Table(
            [
                [p("DEFAULT: DETERMINISTIC", "table_head"), p("OPTIONAL: OPENAI", "table_head")],
                [p("Offline, reproducible, zero API cost. Keyword and rule-based categories feed the same transparent score and follow-up logic.", "table"), p("Responses API with strict Structured Outputs, store: false, bounded retries, and a second local schema validation pass.", "table")],
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
             ["", p("Media type, byte count, object shape, source, and message length are validated.", "small"), "", p("Deterministic rules or validated model output become bounded fields.", "small"), "", p("Lead, duplicate state, and event log are persisted under one process lock.", "small")]],
            colWidths=[0.3 * inch, 1.92 * inch] * 3,
            style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEABOVE", (0, 0), (-1, 0), 0.8, LINE), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]),
        ),
        PageBreak(),
        p("ENGINEERING AND VERIFICATION", "eyebrow"),
        p("Built for credible review", "title"),
        p("The portfolio value is not a claim of a live CRM deployment. It is an inspectable reference architecture with explicit privacy, security, and operating boundaries.", "subtitle"),
        Table(
            [
                [p("Reliable persistence", "h3"), p("Safer interfaces", "h3")],
                [[bullet("Thread-safe read/modify/write operations"), bullet("Atomic tempfile + replace writes"), bullet("Corrupt JSON shape detection"), bullet("Runtime data excluded from Git")], [bullet("Generic server errors"), bullet("HTML escaping and allowlisted classes"), bullet("Formula-safe CSV cells"), bullet("No-cache and browser security headers")]],
            ],
            colWidths=[3.35 * inch, 3.35 * inch],
            style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE), ("BOX", (0, 0), (-1, -1), 0.7, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 9)]),
        ),
        p("Privacy by default", "h2"),
        bullet("Raw inquiry text is not retained unless STORE_RAW_MESSAGE=1 is deliberately enabled."),
        bullet("API keys, provider bodies, and lead text are excluded from logs."),
        bullet("OpenAI mode sends only the normalized inquiry needed for the requested classification and sets store: false."),
        p("Verification evidence", "h2"),
        Table(
            [[p("39", "number"), p("isolated tests", "h3"), p("3", "number"), p("Python versions in CI", "h3"), p("2", "number"), p("reproducible PDFs", "h3")],
             ["", p("Analysis, extraction, provider, storage, concurrency, CSV, HTML, and local HTTP behavior.", "small"), "", p("Python 3.11, 3.12, and 3.13 run the same standard-library suite.", "small"), "", p("Build, page count, metadata, and required text are checked in CI.", "small")]],
            colWidths=[0.45 * inch, 1.78 * inch] * 3,
            style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE), ("BOX", (0, 0), (-1, -1), 0.7, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 7)]),
        ),
        p("Client adaptation path", "h2"),
        p("After requirements discovery, the same validated record can be connected to an authenticated form or inbox and written through an official CRM API. Production delivery would add identity and access controls, TLS, rate limits, a managed transactional database, retention/deletion automation, monitoring, backups, and reconciliation."),
        p("Honest scope", "h2"),
        p("This repository demonstrates the engineering pattern. It does not claim active Gmail, HubSpot, Airtable, Google Sheets, Pipedrive, GoHighLevel, Zapier, Make, or n8n integrations. A paid live OpenAI smoke test also requires the project owner's API key; all other behavior is locally and continuously verified."),
    ]
    doc(path, "AI CRM Lead Automation - Case Study").build(story, onFirstPage=page_frame, onLaterPages=page_frame)


def build_technical_summary() -> None:
    path = OUTPUT / "AI-CRM-Lead-Automation-Technical-Summary.pdf"
    endpoints = [
        [p("METHOD", "table_head"), p("ROUTE", "table_head"), p("PURPOSE", "table_head")],
        [p("GET", "table"), p("/ and /api/health", "table"), p("Dashboard and mode-aware health check", "table")],
        [p("POST", "table"), p("/api/intake", "table"), p("Validate, classify, score, and persist one lead", "table")],
        [p("GET", "table"), p("/api/leads and /api/logs", "table"), p("Structured CRM records, metrics, and audit events", "table")],
        [p("GET", "table"), p("/export/leads.csv", "table"), p("Formula-neutralized spreadsheet handoff", "table")],
    ]
    story = [
        p("TECHNICAL SUMMARY", "eyebrow"),
        p("AI CRM Lead Automation", "title"),
        p("Python 3.11+ local reference application | Standard-library runtime | Optional OpenAI Responses API | MIT licensed", "subtitle"),
        summary_strip(),
        p("Architecture", "h2"),
        Table(
            [[p("INTAKE", "table_head"), p("ANALYSIS", "table_head"), p("PERSISTENCE", "table_head"), p("DELIVERY", "table_head")],
             [p("Threaded local HTTP server, strict JSON media type, request/message bounds, normalized object schema.", "table"), p("Deterministic default or strict Structured Outputs; local enums and text limits always enforced.", "table"), p("Process lock, duplicate check, atomic JSON replacement, raw message opt-in only.", "table"), p("Escaped dashboard, JSON endpoints, metrics, event log, formula-safe CSV.", "table")]],
            colWidths=[1.675 * inch] * 4,
            style=TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("BACKGROUND", (0, 1), (-1, 1), PALE), ("BOX", (0, 0), (-1, -1), 0.7, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 7)]),
        ),
        p("HTTP surface", "h2"),
        Table(endpoints, colWidths=[0.7 * inch, 2.05 * inch, 3.95 * inch], repeatRows=1, style=TableStyle([("BACKGROUND", (0, 0), (-1, 0), TEAL), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]), ("BOX", (0, 0), (-1, -1), 0.7, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 6)])),
        p("Security and privacy controls", "h2"),
        Table(
            [[[bullet("Loopback-only host validation"), bullet("Bounded request body and message"), bullet("Safe client-facing errors"), bullet("Security and no-cache headers")], [bullet("HTML and CSS output constraints"), bullet("CSV formula neutralization"), bullet("No secrets or lead text in logs"), bullet("Raw inquiry retention off by default")]]],
            colWidths=[3.35 * inch, 3.35 * inch],
            style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE), ("BOX", (0, 0), (-1, -1), 0.7, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 7)]),
        ),
        p("Verification", "h2"),
        p("39 isolated tests cover deterministic analysis, contact extraction, strict provider output, retries and refusals, corruption handling, duplicate events, atomic/concurrent writes, CSV safety, HTML safety, HTTP limits, routes, methods, errors, and headers. CI runs on Python 3.11-3.13 and rebuilds both PDFs."),
        p("Run locally", "h2"),
        Table([[p("python3 -m unittest discover -s tests -v", "code"), p("python3 src/seed_demo.py", "code"), p("python3 src/app.py", "code")]], colWidths=[2.6 * inch, 2.05 * inch, 2.05 * inch], style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY), ("BOX", (0, 0), (-1, -1), 0.7, NAVY), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("PADDING", (0, 0), (-1, -1), 7)])),
        Spacer(1, 0.04 * inch),
        p("Deployment boundary: single-machine reference implementation. Production use requires authentication, TLS, rate limits, managed persistence, monitoring, backups, and formal data lifecycle controls.", "small"),
    ]
    doc(path, "AI CRM Lead Automation - Technical Summary").build(story, onFirstPage=page_frame, onLaterPages=page_frame)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    build_case_study()
    build_technical_summary()
    for path in sorted(OUTPUT.glob("*.pdf")):
        print(f"Built {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
