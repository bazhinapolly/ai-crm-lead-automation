# Client Verification Report

## What A Client Can Verify

This demo can be checked locally without creating accounts, buying subscriptions, or adding an API key.

## Verification Steps

1. Run demo data:

```bash
python3 src/seed_demo.py
```

2. Run automated checks:

```bash
python3 src/test_workflow.py
```

Expected result:

```text
All workflow tests passed.
```

3. Start the dashboard:

```bash
python3 src/app.py
```

4. Open:

```text
http://127.0.0.1:8080
```

If port `8080` is already busy, start the app with:

```bash
PORT=8090 python3 src/app.py
```

Then open:

```text
http://127.0.0.1:8090
```

5. Confirm that the dashboard shows lead metrics, lead rows, priority labels, follow-up dates, AI summaries, and CSV export.

6. Submit a new lead from the dashboard form and confirm that the CRM table updates.

7. Test the API:

```bash
curl http://127.0.0.1:8080/api/health
```

Expected result:

```json
{
  "ok": true,
  "service": "ai-crm-lead-automation"
}
```

## Reliability Features

- Empty message validation
- Duplicate detection by email
- Event logging for created leads and duplicates
- Deterministic demo mode for repeatable testing
- CSV export for spreadsheet handoff

## What This Demonstrates

This project demonstrates practical CRM automation thinking: intake, extraction, scoring, routing, follow-up planning, dashboard visibility, documentation, and testable delivery.
