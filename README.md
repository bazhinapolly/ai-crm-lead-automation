# AI CRM Lead Automation

[![CI](https://github.com/bazhinapolly/ai-crm-lead-automation/actions/workflows/ci.yml/badge.svg)](https://github.com/bazhinapolly/ai-crm-lead-automation/actions/workflows/ci.yml)

A portfolio-grade local application that turns inbound messages into structured CRM records, priorities, follow-up dates, and safe CSV exports. It works offline and at zero API cost by default; an optional OpenAI Responses API provider adds strict Structured Outputs without changing the CRM contract.

## What is implemented

- Validated `POST /api/intake` endpoint with body limits and safe error responses
- Deterministic service, urgency, budget, intent, and Hot/Warm/Cold scoring
- Optional OpenAI Responses API mode with strict JSON Schema and `store: false`
- Local contact extraction, duplicate detection, follow-up planning, and event logs
- Versioned single-file CRM state with transactional lead-and-event replacement
- Raw lead messages excluded from storage unless explicitly enabled
- PII-redacted OpenAI input and local redaction of generated stored fields
- HTML escaping, constrained CSS classes, security headers, and CSV formula neutralization
- Responsive local dashboard, JSON endpoints, and CSV handoff
- 50 isolated tests, coverage enforcement, and CI on Python 3.11, 3.12, and 3.13

## Local quick start

Requires Python 3.11 or newer. The application itself has no third-party runtime dependencies.

```bash
python3 src/seed_data.py
python3 src/app.py
```

Open <http://127.0.0.1:8080>. Use `PORT=8090 python3 src/app.py` if port 8080 is busy.

Runtime leads and logs are created under `data/` and ignored by Git. To keep local data elsewhere:

```bash
CRM_DATA_DIR=/tmp/crm-data python3 src/seed_data.py
CRM_DATA_DIR=/tmp/crm-data python3 src/app.py
```

## Verify the project

```bash
python3 -m unittest discover -s tests -v
python3 tools/check_project.py --skip-pdf
```

To rebuild and validate the Upwork portfolio PDFs:

```bash
python3 -m pip install -r requirements-dev.txt
python3 tools/build_portfolio_pdfs.py
python3 tools/check_project.py
```

Final PDFs are written to [`output/pdf`](output/pdf). Temporary render files are not committed.

## API

```bash
curl http://127.0.0.1:8080/api/health

curl -X POST http://127.0.0.1:8080/api/intake \
  -H 'Content-Type: application/json' \
  -d '{"source":"website_form","message":"Hi, this is Sarah from Oakwood Dental. We need appointment automation urgently. Budget is $1500. Email sarah@example.com."}'
```

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/` | Local CRM dashboard |
| `GET` | `/api/health` | Health and analysis mode |
| `GET` | `/api/leads` | Leads plus pipeline metrics |
| `GET` | `/api/logs` | Automation event log |
| `POST` | `/api/intake` | Validate and classify one lead |
| `GET` | `/export/leads.csv` | Spreadsheet-safe CSV export |

## Optional OpenAI mode

Export variables in your shell; this project deliberately does not auto-load `.env` files.

```bash
export USE_OPENAI=1
export OPENAI_API_KEY='your-key'
export OPENAI_MODEL='gpt-4o-mini-2024-07-18'
python3 src/app.py
```

Contact fields are extracted locally. Before an OpenAI request, the provider input removes detected names and companies plus email addresses, phone numbers, and long account-like numbers. Budget amounts and classification-relevant language are retained. Generated summaries and replies pass through the local redactor again before storage. Redaction is best-effort and must be evaluated against the target intake channel.

The integration uses the [Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create), [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), `store: false`, strict local validation, bounded transient retries, and content-free provider logging. API keys, provider bodies, and lead text are never written to application logs. Separate OpenAI abuse-monitoring retention remains subject to the configured project's [data controls](https://developers.openai.com/api/docs/guides/your-data).

## Scoring policy and evaluation

Weights, service bonuses, and Hot/Warm/Cold thresholds live in [`config/scoring-policy.json`](config/scoring-policy.json). A balanced synthetic regression set and confusion-matrix evaluator are documented in [`docs/scoring-evaluation.md`](docs/scoring-evaluation.md). The checked deterministic policy result is 15/15; it demonstrates specification conformance, not real-world sales performance. Optional OpenAI evaluation requires the project owner's API key and does not claim an unverified score.

## Security and deployment boundary

This local-first application intentionally binds to a single machine. Production rollout adds authentication, authorization, TLS, a managed database, retention/deletion controls, rate limiting, observability, backups, and the target CRM's official API. See [`docs/privacy-and-operations.md`](docs/privacy-and-operations.md).

The architecture provides documented integration points for HubSpot, Airtable, Google Sheets, Gmail, Zapier, Make, and n8n connectors selected for a client environment.

## Project map

```text
src/                 local application, analysis, provider, and storage
config/              versioned lead-scoring policy
tests/               isolated unit and local HTTP integration tests
evaluations/         synthetic scoring regression cases
data/                sample inputs; runtime CRM files are ignored
docs/                case-study source and operating boundaries
tools/               PDF builder and repository checks
output/pdf/          final Upwork-ready portfolio documents
.github/workflows/   multi-version CI and validated PDF rebuild
```

## License

[MIT](LICENSE) - Copyright 2026 Polina Bazhina.
