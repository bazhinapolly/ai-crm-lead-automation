"""Thread-safe transactional state storage for the local CRM application."""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
import tempfile
import threading
import uuid
from io import StringIO
from pathlib import Path

from lead_ai import AnalysisProvider, analysis_to_dict, analyze_lead, extract_contact


class DataStoreError(RuntimeError):
    """Raised when persisted data is missing its expected structure."""


class JsonCRM:
    SCHEMA_VERSION = 1

    def __init__(
        self,
        data_dir: Path,
        *,
        provider: AnalysisProvider | None = None,
        store_raw_message: bool = False,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.state_file = self.data_dir / "crm_state.json"
        self.legacy_leads_file = self.data_dir / "leads.json"
        self.legacy_logs_file = self.data_dir / "automation_logs.json"
        self.provider = provider
        self.store_raw_message = store_raw_message
        self._lock = threading.RLock()
        self._ensure_files()

    def _ensure_files(self) -> None:
        with self._lock:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            if self.state_file.exists():
                self._load_state(); return
            leads = self._load_collection(self.legacy_leads_file) if self.legacy_leads_file.exists() else []
            logs = self._load_collection(self.legacy_logs_file) if self.legacy_logs_file.exists() else []
            self._atomic_write_state({"schema_version": self.SCHEMA_VERSION, "leads": leads, "logs": logs})

    @staticmethod
    def _load_collection(path: Path) -> list[dict[str, object]]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise DataStoreError(f"Unable to read valid CRM data from {path.name}") from exc
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            raise DataStoreError(f"CRM data in {path.name} must be a list of objects")
        return value

    def _load_state(self) -> dict[str, object]:
        try:
            state = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise DataStoreError("Unable to read valid CRM data from crm_state.json") from exc
        if not isinstance(state, dict) or set(state) != {"schema_version", "leads", "logs"}:
            raise DataStoreError("CRM data in crm_state.json has an invalid state schema")
        if state["schema_version"] != self.SCHEMA_VERSION:
            raise DataStoreError("CRM data in crm_state.json uses an unsupported schema version")
        for key in ("leads", "logs"):
            if not isinstance(state[key], list) or any(not isinstance(item, dict) for item in state[key]):
                raise DataStoreError(f"CRM {key} in crm_state.json must be a list of objects")
        return state

    @staticmethod
    def _atomic_write(path: Path, records: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(records, stream, indent=2, ensure_ascii=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        except BaseException:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise

    def _atomic_write_state(self, state: dict[str, object]) -> None:
        self._atomic_write(self.state_file, state)

    def list_leads(self) -> list[dict[str, object]]:
        with self._lock:
            return sorted(self._load_state()["leads"], key=lambda item: str(item.get("received_at", "")), reverse=True)

    def list_logs(self) -> list[dict[str, object]]:
        with self._lock:
            return sorted(self._load_state()["logs"], key=lambda item: str(item.get("created_at", "")), reverse=True)

    def create_lead(self, source: str, message: str, now: dt.datetime | None = None) -> dict[str, object]:
        now = now or dt.datetime.now(dt.timezone.utc)
        contact = extract_contact(message)
        analysis = analysis_to_dict(analyze_lead(message, now, self.provider))
        lead_id = uuid.uuid4().hex[:12]
        lead: dict[str, object] = {
            "id": lead_id,
            "received_at": now.isoformat(timespec="seconds"),
            "source": source,
            "status": "New",
            "owner": "Unassigned",
            **contact,
            **analysis,
        }
        if self.store_raw_message:
            lead["raw_message"] = message

        with self._lock:
            state = self._load_state()
            leads = state["leads"]
            logs = state["logs"]
            duplicate = self.find_duplicate(leads, lead)
            if duplicate:
                lead["status"] = "Duplicate Review"
                logs.append(self._event("duplicate_detected", lead_id, f"Possible duplicate of lead {duplicate['id']}", now))
            leads.append(lead)
            logs.append(self._event("lead_created", lead_id, f"Created {lead['priority_label']} lead from {source}", now))
            self._atomic_write_state(state)
        return lead

    @staticmethod
    def find_duplicate(leads: list[dict[str, object]], lead: dict[str, object]) -> dict[str, object] | None:
        email = str(lead.get("email", "")).casefold()
        return next((item for item in leads if email and str(item.get("email", "")).casefold() == email), None)

    @staticmethod
    def _event(event_type: str, lead_id: str, message: str, now: dt.datetime) -> dict[str, object]:
        return {
            "id": uuid.uuid4().hex[:12],
            "created_at": now.isoformat(timespec="seconds"),
            "event_type": event_type,
            "lead_id": lead_id,
            "message": message,
        }

    def pipeline_metrics(self) -> dict[str, int | float]:
        leads = self.list_leads()
        count = lambda label: sum(item.get("priority_label") == label for item in leads)
        scores = [item.get("priority_score") for item in leads if isinstance(item.get("priority_score"), int)]
        return {
            "total_leads": len(leads),
            "hot_leads": count("Hot"),
            "warm_leads": count("Warm"),
            "cold_leads": count("Cold"),
            "follow_up_today": sum(item.get("pipeline_stage") == "Contact Today" for item in leads),
            "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
        }

    def export_leads_csv(self) -> str:
        fields = [
            "id", "received_at", "source", "name", "email", "company", "service_needed",
            "priority_label", "priority_score", "pipeline_stage", "follow_up_date", "status",
            "next_action", "ai_summary", "analysis_mode",
        ]
        output = StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\r\n")
        writer.writeheader()
        for lead in self.list_leads():
            writer.writerow({field: csv_safe(lead.get(field, "")) for field in fields})
        return output.getvalue()

    def reset(self) -> None:
        with self._lock:
            self._atomic_write_state({"schema_version": self.SCHEMA_VERSION, "leads": [], "logs": []})


def csv_safe(value: object) -> object:
    if not isinstance(value, str):
        return value
    if value.startswith(("\t", "\r")) or value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value
