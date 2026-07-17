# Privacy, Security, and Operations

## Data handling

Lead messages can contain names, email addresses, phone numbers, business details, and free-form personal data. The application stores extracted CRM fields and a bounded analysis summary but excludes the raw message by default. Set `STORE_RAW_MESSAGE=1` only after defining a legitimate purpose, access policy, retention period, and deletion process.

Optional OpenAI mode extracts contact fields locally, then redacts detected names, companies, email addresses, phone numbers, and long account-like numbers before sending the classification-relevant inquiry to the configured OpenAI project. Budget amounts are retained because they affect scoring. Generated summaries and replies are redacted locally again before storage. Pattern-based redaction is best-effort and cannot guarantee anonymization.

Extracted contact fields use a configurable 90-day retention window by default. Retention is applied explicitly with `python3 src/purge_data.py`; individual records can be exported with `GET /api/leads/{id}` and removed with `DELETE /api/leads/{id}`. Deletion and purge events contain lead IDs and operational metadata, not contact values.

Every persisted lead must have a timezone-aware ISO `received_at` value. Startup and purge fail safely when that invariant is broken, requiring operator repair instead of silently retaining an invalid contact indefinitely. Successful migration removes legacy `leads.json` and `automation_logs.json`; if the new atomic state write fails, legacy files remain untouched for recovery. Operators must also remove separately created backups according to their approved retention policy.

Requests set `store: false`, which disables Responses application-state storage for the request. This does not by itself remove separate provider abuse-monitoring logs. Operators must review the current OpenAI data controls, selected project settings, contracts, and applicable law before processing real personal data.

## Local controls

- Numeric loopback binding is enforced.
- A strong optional local key protects bearer API access and browser sessions; sessions have a sliding TTL and logout, session-authenticated writes require CSRF tokens, and failed sign-ins are throttled with thread-safe state.
- A bounded per-IP intake limiter applies in both modes; optional OpenAI mode also caps concurrent provider calls and returns `429` with `Retry-After` when either control is reached.
- Request bodies and normalized message length are bounded.
- JSON media type and object shape are validated.
- Application errors do not expose tracebacks, provider bodies, or secrets to clients.
- API keys, raw model responses, and lead text are excluded from logs.
- Lead records and event logs share one versioned state file. Every transaction uses a shared per-path thread lock plus an OS-level interprocess file lock, then commits with one atomic replacement.
- CSV values that could become spreadsheet formulas are neutralized.

## Production adaptation checklist

Production rollout of the local application includes:

1. Mandatory authenticated and authorized endpoints with tenant isolation.
2. TLS termination, CSRF/CORS policy, rate limiting, and abuse controls.
3. A transactional managed database with migrations, backups, and recovery tests.
4. Encryption, secrets management, scheduled retention/deletion automation, and audit policy.
5. Monitoring, alerting, tracing, queue/retry strategy, and provider budget limits.
6. Data-processing agreements and an approved privacy/security review.
7. Official CRM/source connectors with idempotency and reconciliation.
