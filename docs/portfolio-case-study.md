# AI CRM Lead Automation - Portfolio Case Study

## Challenge

Inbound leads often arrive through several disconnected channels. Small teams then copy contact data into spreadsheets, interpret urgency manually, and remember follow-ups without a consistent process. That creates slow responses, incomplete records, and weak pipeline visibility.

## Solution

I built a local portfolio workflow that converts an unstructured lead message into a bounded CRM record. The application validates the request, extracts contact details, classifies the request, calculates a transparent priority score, assigns a follow-up date, detects duplicate email addresses, records automation events, and exposes the result through a dashboard, JSON API, and CSV export.

Two analysis modes share the same validated contract:

- Deterministic mode is the safe default. It is offline, repeatable, and free to run.
- Optional OpenAI mode uses locally redacted input, strict Structured Outputs, `store: false`, bounded retries, local validation, and generated-field redaction.

## Engineering highlights

- Transactional lead and event updates in one versioned CRM state
- Atomic temporary-file replacement to prevent partial commits
- OS-level interprocess file locking around every state transaction
- Legacy JSON removal only after a validated successful migration
- Isolated test data so verification never mutates portfolio project files
- Request byte and message-length limits, exact JSON media-type checks, and generic server errors
- HTML escaping and allowlisted priority classes in the dashboard
- Spreadsheet formula neutralization in CSV exports
- Raw inquiry retention disabled by default as a privacy boundary
- 69 automated tests, 90% overall coverage enforcement, and CI on Python 3.11, 3.12, and 3.13

## Outcome

The result is a credible, inspectable lead-triage architecture designed for adaptation to a client's authenticated form, inbox, CRM, or automation platform after access, retention, and operational requirements are defined.

## Scope boundary

The project is a single-machine local application with documented integration points for Gmail, HubSpot, Airtable, Google Sheets, Pipedrive, GoHighLevel, Zapier, Make, and n8n. Production rollout makes authentication and authorization mandatory and adds TLS, managed persistence, rate limiting, monitoring, backups, and formal data lifecycle controls. No client deployment, client acceptance, or measured business outcome is claimed.
