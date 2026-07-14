# Privacy, Security, and Operations

## Data handling

Lead messages can contain names, email addresses, phone numbers, business details, and free-form personal data. The application stores extracted CRM fields and a bounded analysis summary but excludes the raw message by default. Set `STORE_RAW_MESSAGE=1` only after defining a legitimate purpose, access policy, retention period, and deletion process.

Optional OpenAI mode sends the normalized inquiry text to the configured OpenAI API project for analysis. It sets `store: false`; operators must still review current provider terms and configure their account appropriately before processing real personal data.

## Local controls

- Numeric loopback binding is enforced.
- Request bodies and normalized message length are bounded.
- JSON media type and object shape are validated.
- Application errors do not expose tracebacks, provider bodies, or secrets to clients.
- API keys, raw model responses, and lead text are excluded from logs.
- JSON writes use a process-local lock and atomic file replacement.
- CSV values that could become spreadsheet formulas are neutralized.

## Production adaptation checklist

This reference app is not an internet-facing deployment. Before production use, add:

1. Authenticated and authorized endpoints with tenant isolation.
2. TLS termination, CSRF/CORS policy, rate limiting, and abuse controls.
3. A transactional managed database with migrations, backups, and recovery tests.
4. Encryption, secrets management, retention/deletion automation, and audit policy.
5. Monitoring, alerting, tracing, queue/retry strategy, and provider budget limits.
6. Data-processing agreements and an approved privacy/security review.
7. Official CRM/source connectors with idempotency and reconciliation.
