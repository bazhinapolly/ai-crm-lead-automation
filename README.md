# AI CRM Lead Automation System

A practical CRM lead automation workflow for small service businesses. It captures incoming lead messages, analyzes them with AI-style structured extraction, stores them in a lightweight CRM, generates follow-up suggestions, and shows a browser dashboard.

This portfolio case study is designed to show the type of automation small businesses often need: fewer missed leads, faster follow-ups, clearer pipeline visibility, and less manual admin work.

## What It Does

- Accepts incoming lead messages through a local webhook-style endpoint
- Extracts lead details from email, form, or chat-style text
- Classifies service type, urgency, budget signal, intent, and next action
- Scores leads as Hot, Warm, or Cold
- Stores leads in a JSON-backed mini CRM
- Shows a browser dashboard with lead status and follow-up priorities
- Exports leads to CSV for Google Sheets or Airtable-style workflows
- Includes local verification mode so the workflow can be tested without an API key
- Includes an OpenAI-ready analysis layer for real client adaptation

## Why This Matters

Many small businesses receive leads from Gmail, website forms, chat widgets, referrals, or ads. Those leads often get copied manually into spreadsheets or CRMs, and follow-ups are easy to miss.

This project shows a practical automation pattern:

```text
Gmail/Form/Webhook -> AI Lead Analysis -> CRM Record -> Follow-up Plan -> Dashboard -> Export/Integration
```

## Tech Stack

- Python standard library
- Local HTTP server
- JSON storage
- CSV export
- Browser dashboard
- OpenAI-ready AI analysis layer

No external dependencies are required for local verification mode.

## Project Structure

```text
ai-crm-lead-automation/
  src/
    app.py
    lead_ai.py
    storage.py
    seed_demo.py
    test_workflow.py
  data/
    sample_messages.json
    leads.json
    automation_logs.json
  docs/
    portfolio-case-study.md
    client-verification-report.md
    workflow-diagram.md
    AI-CRM-Lead-Automation-Case-Study.pdf
    AI-CRM-Lead-Automation-Technical-Summary.pdf
  .env.example
  README.md
```

## Quick Start

From this project folder:

```bash
python3 src/seed_demo.py
python3 src/test_workflow.py
python3 src/app.py
```

Then open:

```text
http://127.0.0.1:8080
```

If port `8080` is already in use, run the application on another port:

```bash
PORT=8090 python3 src/app.py
```

## API Examples

Health check:

```bash
curl http://127.0.0.1:8080/api/health
```

Submit a new lead:

```bash
curl -X POST http://127.0.0.1:8080/api/intake \
  -H "Content-Type: application/json" \
  -d '{"source":"website_form","message":"Hi, my name is Sarah from Oakwood Dental. We need help automating appointment reminders and follow-ups. Please call me this week. Budget is around $1500."}'
```

Export leads to CSV:

```text
http://127.0.0.1:8080/export/leads.csv
```

## Local Verification vs Real Client Mode

The default version uses deterministic local lead analysis so the workflow can be verified without API costs or an exposed API key.

For a real client implementation, the `analyze_lead()` layer can be connected to OpenAI, Claude, Gemini, or another model while preserving the same structured CRM fields.

## Use Cases

- Contractor lead tracking
- Agency inquiry routing
- Clinic appointment requests
- Consulting discovery calls
- Home service quote follow-ups
- B2B inbound lead triage
- CRM cleanup and prioritization

## Business Value

This type of automation helps businesses respond to leads faster, reduce manual CRM work, avoid missed opportunities, keep lead data organized, and give the team a clear view of which prospects should be contacted first.

## Portfolio Context

This is a portfolio case study built to show the architecture, workflow logic, structured AI output, dashboard, CSV export, and documentation patterns behind a practical CRM lead automation system.

It can be adapted to Google Sheets, Airtable, HubSpot, GoHighLevel, Pipedrive, Zapier, Make, n8n, or other CRM and automation platforms.