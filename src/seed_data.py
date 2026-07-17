"""Seed an isolated or configured local CRM with sample messages."""

from __future__ import annotations

import json
import argparse

from app import build_store
from config import ROOT_DIR, Settings


def load_samples(path) -> list[dict[str, str]]:
    try:
        samples = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("sample input must be readable JSON") from exc
    if not isinstance(samples, list) or not samples: raise ValueError("sample input must be a non-empty list")
    for sample in samples:
        if not isinstance(sample, dict) or set(sample) != {"source", "message"} or not all(isinstance(sample[key], str) and sample[key].strip() for key in ("source", "message")):
            raise ValueError("every sample must contain non-empty source and message strings")
    return samples


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Seed the local CRM with synthetic portfolio records.")
    parser.add_argument("--reset", action="store_true", help="destructively clear existing leads and logs before seeding")
    args = parser.parse_args(argv)
    settings = Settings.from_env()
    samples = load_samples(ROOT_DIR / "data" / "sample_messages.json")
    store = build_store(settings)
    if store.list_leads() or store.list_logs():
        if not args.reset:
            raise SystemExit("CRM state is not empty. Re-run with --reset only if destructive replacement is intended.")
        store.reset()
    for sample in samples:
        store.create_lead(sample["source"], sample["message"])
    print(f"Seeded {len(samples)} sample leads in {settings.data_dir}.")


if __name__ == "__main__":
    main()
