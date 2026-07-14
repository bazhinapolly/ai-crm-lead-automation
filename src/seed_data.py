"""Seed an isolated or configured local CRM with sample messages."""

from __future__ import annotations

import json

from app import build_store
from config import ROOT_DIR, Settings


def main() -> None:
    settings = Settings.from_env()
    samples = json.loads((ROOT_DIR / "data" / "sample_messages.json").read_text(encoding="utf-8"))
    store = build_store(settings)
    store.reset()
    for sample in samples:
        store.create_lead(sample["source"], sample["message"])
    print(f"Seeded {len(samples)} sample leads in {settings.data_dir}.")


if __name__ == "__main__":
    main()
