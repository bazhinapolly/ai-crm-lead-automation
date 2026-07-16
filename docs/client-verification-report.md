# Client Verification Report

Verified locally on 2026-07-15:

- Python source and tests compile successfully.
- All 50 isolated automated tests pass with the enforced branch-coverage threshold.
- Parallel lead creation preserves every record and event; fault injection confirms lead and event state cannot be partially committed.
- Local HTTP integration tests cover intake, errors, limits, routes, methods, and security headers.
- OpenAI provider tests mock successful, refused, incomplete, transient, and permanent responses; separate tests verify input and generated-field PII redaction without spending API credit.
- The balanced 15-case scoring specification reports 100% precision and recall for Hot, Warm, and Cold policy labels.
- Both portfolio PDFs rebuild from source, pass text/page checks, and were rendered for visual inspection.

CI repeats coverage and the scoring regression on Python 3.11, 3.12, and 3.13 and independently rebuilds both PDFs.

One external check is intentionally excluded: a paid live OpenAI request requires the project owner's API key. The default deterministic workflow is fully testable without it.
