"""Check repository structure and generated portfolio PDF contracts."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md", "LICENSE", ".env.example", ".gitignore",
    ".github/workflows/ci.yml", "src/app.py", "src/config.py", "src/lead_ai.py",
    "src/openai_provider.py", "src/storage.py", "tests/test_app.py",
    "tests/test_lead_ai.py", "tests/test_openai_provider.py", "tests/test_storage.py",
    "tests/test_config_and_startup.py", "config/scoring-policy.json",
    "evaluations/scoring-cases.json", "docs/privacy-and-operations.md",
    "docs/scoring-evaluation.md", "docs/local-technical-verification-report.md",
    "tools/evaluate_scoring.py", "tools/build_portfolio_pdfs.py",
]
PDFS = {
    "AI-CRM-Lead-Automation-Case-Study.pdf": (2, ("AI CRM Lead Automation", "69", "interprocess", "Integration scope")),
    "AI-CRM-Lead-Automation-Technical-Summary.pdf": (1, ("AI CRM Lead Automation", "interprocess file lock", "f892334", "Production rollout")),
}
FORBIDDEN_PDF_WORDING = (
    r"\bdemo\b",
    r"\beducational\b",
    r"\blearning project\b",
    r"reference app",
    r"reference implementation",
    r"not a live",
)


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_structure() -> None:
    missing = [item for item in REQUIRED if not (ROOT / item).is_file()]
    if missing:
        fail(f"missing required files: {', '.join(missing)}")
    forbidden = [path for path in ROOT.rglob("*") if path.name in {".DS_Store", "client-verification-report.md"} or "docs - " in path.name]
    if forbidden:
        fail(f"generated or duplicate files remain: {', '.join(str(path.relative_to(ROOT)) for path in forbidden[:5])}")


def check_pdfs() -> None:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        fail("pypdf is required unless --skip-pdf is used")
        raise AssertionError from exc
    output = ROOT / "output" / "pdf"
    for filename, (expected_pages, phrases) in PDFS.items():
        path = output / filename
        if not path.is_file() or path.stat().st_size < 3_000:
            fail(f"missing or unexpectedly small PDF: {path.relative_to(ROOT)}")
        reader = PdfReader(path)
        if len(reader.pages) != expected_pages:
            fail(f"{filename} has {len(reader.pages)} pages; expected {expected_pages}")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        for phrase in phrases:
            if phrase not in text:
                fail(f"{filename} is missing required text: {phrase}")
        for pattern in FORBIDDEN_PDF_WORDING:
            if re.search(pattern, text, flags=re.IGNORECASE):
                fail(f"{filename} contains forbidden portfolio wording: {pattern}")
        if any(character in text for character in "‐‑‒–—―"):
            fail(f"{filename} contains a non-ASCII hyphen character")
        print(f"Checked {filename}: {len(reader.pages)} page(s), {path.stat().st_size} bytes")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-pdf", action="store_true")
    args = parser.parse_args()
    check_structure()
    if not args.skip_pdf:
        check_pdfs()
    print("Project checks passed.")


if __name__ == "__main__":
    main()
