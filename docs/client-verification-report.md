# Client Verification Report

Verified locally on 2026-07-15:

- Python source and tests compile successfully.
- All 39 isolated automated tests pass.
- Parallel lead creation preserves every record and log entry.
- Local HTTP integration tests cover intake, errors, limits, routes, methods, and security headers.
- OpenAI provider tests mock successful, refused, incomplete, transient, and permanent responses without spending API credit.
- Both portfolio PDFs rebuild from source, pass text/page checks, and were rendered for visual inspection.

CI repeats the test suite on Python 3.11, 3.12, and 3.13 and independently rebuilds both PDFs.

One external check is intentionally excluded: a paid live OpenAI request requires the project owner's API key. The default deterministic workflow is fully testable without it.
