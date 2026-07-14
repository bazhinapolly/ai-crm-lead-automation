"""Seed the demo CRM with sample inbound lead messages."""

from __future__ import annotations

import json
from pathlib import Path

from storage import ROOT_DIR, create_lead, reset_demo_data


def main() -> None:
    sample_path = ROOT_DIR / "data" / "sample_messages.json"
    samples = json.loads(sample_path.read_text(encoding="utf-8"))

    reset_demo_data()
    for sample in samples:
        create_lead(sample["source"], sample["message"])

    print(f"Seeded {len(samples)} demo leads.")


if __name__ == "__main__":
    main()

