# Local Technical Verification Report

Verified locally on 2026-07-17 for release `v2.1.0`.

Scope: local portfolio verification with synthetic data. No client deployment, client acceptance, production operation, or measured business outcome is claimed.

## Verified results

- Python source and tests compile successfully.
- All 76 isolated automated tests pass with the enforced 90% overall coverage threshold.
- Overall coverage is 91%; `storage.py` is 91%, `app.py` is 88%, `lead_ai.py` is 95%, and `openai_provider.py` is 97%.
- A mandatory multiprocessing regression test starts six independent processes against one CRM directory and preserves all six leads and all six events.
- Every state read-modify-write transaction is protected by a per-path thread lock and an OS-level interprocess file lock.
- Legacy `leads.json` and `automation_logs.json` are removed only after a validated atomic migration; simulated write failure preserves the source files.
- Retention rejects missing, malformed, or timezone-free `received_at` values instead of silently retaining contact data forever.
- Concurrent browser verification covers thread-safe session access and exact login-attempt throttling; separate tests cover session TTL, sliding activity expiry, CSRF, and logout/cookie clearing.
- Bounded per-IP intake control returns `429` and `Retry-After`; OpenAI mode also rejects work above its configurable concurrent-provider cap.
- Sentence-final, parenthesized, quoted, comma-delimited, subdomain, plus-addressed, and multiple-email cases are extracted and redacted with one shared compiled pattern.
- OpenAI provider tests mock successful, refused, incomplete, transient, and permanent responses without spending API credit.
- The balanced 15-case scoring specification reports 100% precision and recall for Hot, Warm, and Cold policy labels. This is specification conformance on synthetic cases, not sales-performance evidence.
- Both portfolio PDFs rebuild deterministically and are checked for text, page count, and visual layout.

CI repeats coverage, multiprocessing, and the scoring regression on Python 3.11, 3.12, and 3.13 and independently rebuilds both PDFs.

One external check remains intentionally excluded: a paid live OpenAI request requires the project owner's API key. The default deterministic workflow is fully testable without it, and no live model-quality score is claimed.
