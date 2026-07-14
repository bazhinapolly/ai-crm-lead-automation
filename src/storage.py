"""JSON-backed storage for the AI CRM Lead Automation demo."""

from __future__ import annotations

import csv
import datetime as dt
import json
import uuid
from pathlib import Path

from lead_ai import analyze_lead, analysis_to_dict, extract_contact


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
LEADS_FILE = DATA_DIR / "leads.json"
LOGS_FILE = DATA_DIR / "automation_logs.json"


def ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not LEADS_FILE.exists():
        LEADS_FILE.write_text("[]\n", encoding="utf-8")
    if not LOGS_FILE.exists():
        LOGS_FILE.write_text("[]\n", encoding="utf-8")


def load_json(path: Path) -> list[dict]:
    ensure_data_files()
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, records: list[dict]) -> None:
    ensure_data_files()
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def list_leads() -> list[dict]:
    return sorted(load_json(LEADS_FILE), key=lambda lead: lead["received_at"], reverse=True)


def list_logs() -> list[dict]:
    return sorted(load_json(LOGS_FILE), key=lambda log: log["created_at"], reverse=True)


def create_lead(source: str, message: str, now: dt.datetime | None = None) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    source = source or "manual"
    message = message.strip()

    if not message:
        raise ValueError("message is required")

    contact = extract_contact(message)
    analysis = analysis_to_dict(analyze_lead(message, now))
    lead_id = str(uuid.uuid4())[:8]

    lead = {
        "id": lead_id,
        "received_at": now.isoformat(timespec="seconds"),
        "source": source,
        "status": "New",
        "owner": "Unassigned",
        "raw_message": message,
        **contact,
        **analysis,
    }

    leads = list_leads()
    duplicate = find_duplicate(leads, lead)
    if duplicate:
        lead["status"] = "Duplicate Review"
        log_event("duplicate_detected", lead_id, f"Possible duplicate of lead {duplicate['id']}")

    leads.append(lead)
    save_json(LEADS_FILE, leads)
    log_event("lead_created", lead_id, f"Created {lead['priority_label']} lead from {source}")
    return lead


def find_duplicate(leads: list[dict], lead: dict) -> dict | None:
    email = lead.get("email")
    if not email:
        return None
    for existing in leads:
        if existing.get("email", "").lower() == email.lower():
            return existing
    return None


def log_event(event_type: str, lead_id: str, message: str) -> None:
    logs = load_json(LOGS_FILE)
    logs.append(
        {
            "id": str(uuid.uuid4())[:8],
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "event_type": event_type,
            "lead_id": lead_id,
            "message": message,
        }
    )
    save_json(LOGS_FILE, logs)


def pipeline_metrics() -> dict:
    leads = list_leads()
    hot = [lead for lead in leads if lead["priority_label"] == "Hot"]
    warm = [lead for lead in leads if lead["priority_label"] == "Warm"]
    cold = [lead for lead in leads if lead["priority_label"] == "Cold"]
    follow_up_today = [lead for lead in leads if lead["pipeline_stage"] == "Contact Today"]

    return {
        "total_leads": len(leads),
        "hot_leads": len(hot),
        "warm_leads": len(warm),
        "cold_leads": len(cold),
        "follow_up_today": len(follow_up_today),
        "average_score": round(
            sum(lead["priority_score"] for lead in leads) / len(leads), 1
        )
        if leads
        else 0,
    }


def export_leads_csv() -> str:
    leads = list_leads()
    fields = [
        "id",
        "received_at",
        "source",
        "name",
        "email",
        "company",
        "service_needed",
        "priority_label",
        "priority_score",
        "pipeline_stage",
        "follow_up_date",
        "status",
        "next_action",
        "ai_summary",
    ]
    from io import StringIO

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for lead in leads:
        writer.writerow({field: lead.get(field, "") for field in fields})
    return output.getvalue()


def reset_demo_data() -> None:
    save_json(LEADS_FILE, [])
    save_json(LOGS_FILE, [])

