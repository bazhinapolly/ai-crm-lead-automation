# AI CRM Lead Automation System

## Problem

Small service businesses often receive leads from Gmail, website forms, chat widgets, referrals, and ads. The information is usually copied manually into a spreadsheet or CRM, which creates delays, missed follow-ups, and poor visibility into lead quality.

## Solution

I built a lightweight CRM automation demo that captures an inbound lead message, extracts contact details, classifies the requested service, scores urgency and intent, recommends the next action, stores the lead, and displays everything in a simple dashboard.

## What I Built

- Local webhook-style intake endpoint for new lead messages
- AI-style lead analysis layer with structured output
- Contact extraction for name, email, phone, and company
- Service classification for CRM, Google Workspace, appointment, support, invoice, and reporting workflows
- Hot/Warm/Cold priority scoring
- Follow-up date and next-action generation
- JSON-backed mini CRM storage
- Duplicate detection by email
- Automation event logs
- Browser dashboard for pipeline visibility
- CSV export for Google Sheets, Airtable, HubSpot, Pipedrive, or manual review
- Demo data seeding and verification tests

## Business Impact

This type of workflow helps businesses respond faster, prioritize high-value leads, reduce manual admin work, and avoid losing inquiries inside inboxes or spreadsheets.

## Adaptation Options

The same architecture can be adapted to Gmail, Google Sheets, Airtable, HubSpot, GoHighLevel, Pipedrive, Zapier, Make, n8n, website forms, and chat widgets.
