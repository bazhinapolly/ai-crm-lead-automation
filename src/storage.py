"""Thread-safe transactional state storage for the local CRM application."""

from __future__ import annotations

import csv
import datetime as dt
import fcntl
import json
import os
import tempfile
import threading
import uuid
from contextlib import contextmanager
from io import StringIO
from pathlib import Path

from lead_ai import AnalysisProvider, analysis_to_dict, analyze_lead, extract_contact


class DataStoreError(RuntimeError):
    """Raised when persisted data is missing its expected structure."""


class JsonCRM:
    SCHEMA_VERSION = 1
    _registry_guard = threading.Lock()
    _path_locks: dict[str, threading.RLock] = {}

    def __init__(
        self,
        data_dir: Path,
        *,
        provider: AnalysisProvider | None = None,
        store_raw_message: bool = False,
        retention_days: int = 90,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.state_file = self.data_dir / "crm_state.json"
        self.lock_file = self.data_dir / ".crm_state.lock"
        self.legacy_leads_file = self.data_dir / "leads.json"
        self.legacy_logs_file = self.data_dir / "automation_logs.json"
        self.provider = provider
        self.store_raw_message = store_raw_message
        self.retention_days = retention_days
        lock_key = str(self.data_dir.expanduser().resolve())
        with self._registry_guard:
            self._lock = self._path_locks.setdefault(lock_key, threading.RLock())
        self._ensure_files()

    @contextmanager
    def _state_lock(self, *, exclusive: bool):
        """Coordinate every state transaction across threads, instances, and processes."""
        with self._lock:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with self.lock_file.open("a+", encoding="utf-8") as lock_stream:
                fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
                try:
                    yield
                finally:
                    fcntl.flock(lock_stream.fileno(), fcntl.LOCK_UN)

    def _ensure_files(self) -> None:
        with self._state_lock(exclusive=True):
            if self.state_file.exists():
                self._load_state()
                self._cleanup_legacy_files()
                return
            leads = self._load_collection(self.legacy_leads_file) if self.legacy_leads_file.exists() else []
            logs = self._load_collection(self.legacy_logs_file) if self.legacy_logs_file.exists() else []
            state = {"schema_version": self.SCHEMA_VERSION, "leads": leads, "logs": logs}
            self._validate_state(state)
            self._atomic_write_state(state)
            self._cleanup_legacy_files()

    def _cleanup_legacy_files(self) -> None:
        try:
            self.legacy_leads_file.unlink(missing_ok=True)
            self.legacy_logs_file.unlink(missing_ok=True)
        except OSError as exc:
            raise DataStoreError("Migrated legacy CRM files could not be removed") from exc

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
        self._validate_state(state)
        return state

    def _validate_state(self, state: object) -> None:
        if not isinstance(state, dict) or set(state) != {"schema_version", "leads", "logs"}:
            raise DataStoreError("CRM data in crm_state.json has an invalid state schema")
        if state["schema_version"] != self.SCHEMA_VERSION:
            raise DataStoreError("CRM data in crm_state.json uses an unsupported schema version")
        for key in ("leads", "logs"):
            if not isinstance(state[key], list) or any(not isinstance(item, dict) for item in state[key]):
                raise DataStoreError(f"CRM {key} in crm_state.json must be a list of objects")
        for lead in state["leads"]:
            self._parse_received_at(lead)

    @staticmethod
    def _parse_received_at(lead: dict[str, object]) -> dt.datetime:
        value = lead.get("received_at")
        if not isinstance(value, str) or not value:
            raise DataStoreError("CRM lead has a missing or invalid received_at timestamp")
        try:
            parsed = dt.datetime.fromisoformat(value)
        except ValueError as exc:
            raise DataStoreError("CRM lead has a missing or invalid received_at timestamp") from exc
        if parsed.tzinfo is None:
            raise DataStoreError("CRM lead received_at timestamp must include a timezone")
        return parsed

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
        with self._state_lock(exclusive=False):
            return sorted(self._load_state()["leads"], key=lambda item: str(item.get("received_at", "")), reverse=True)

    def list_logs(self) -> list[dict[str, object]]:
        with self._state_lock(exclusive=False):
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

        with self._state_lock(exclusive=True):
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

    def pipeline_metrics(self, today: dt.date | None = None) -> dict[str, int | float]:
        leads = self.list_leads()
        today = today or dt.datetime.now(dt.timezone.utc).date()
        count = lambda label: sum(item.get("priority_label") == label for item in leads)
        scores = [item.get("priority_score") for item in leads if isinstance(item.get("priority_score"), int)]
        active_due_dates = []
        for item in leads:
            status = str(item.get("status", "")).casefold()
            if status == "duplicate review" or status.startswith("closed"):
                continue
            try:
                active_due_dates.append(dt.date.fromisoformat(str(item.get("follow_up_date", ""))))
            except ValueError:
                continue
        return {
            "total_leads": len(leads),
            "hot_leads": count("Hot"),
            "warm_leads": count("Warm"),
            "cold_leads": count("Cold"),
            "follow_up_today": sum(due == today for due in active_due_dates),
            "overdue": sum(due < today for due in active_due_dates),
            "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
        }

    def export_lead(self, lead_id: str) -> dict[str, object] | None:
        with self._state_lock(exclusive=False):
            lead = next((item for item in self._load_state()["leads"] if item.get("id") == lead_id), None)
            return dict(lead) if lead else None

    def delete_lead(self, lead_id: str, now: dt.datetime | None = None) -> bool:
        now = now or dt.datetime.now(dt.timezone.utc)
        with self._state_lock(exclusive=True):
            state = self._load_state()
            original = len(state["leads"])
            state["leads"] = [item for item in state["leads"] if item.get("id") != lead_id]
            if len(state["leads"]) == original:
                return False
            state["logs"].append(self._event("lead_deleted", lead_id, "Lead deleted by operator", now))
            self._atomic_write_state(state)
            return True

    def purge_expired(self, now: dt.datetime | None = None) -> list[str]:
        now = now or dt.datetime.now(dt.timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=dt.timezone.utc)
        cutoff = now - dt.timedelta(days=self.retention_days)
        with self._state_lock(exclusive=True):
            state = self._load_state()
            retained = []
            removed_ids = []
            for lead in state["leads"]:
                received_at = self._parse_received_at(lead)
                if received_at < cutoff:
                    removed_ids.append(str(lead.get("id", "")))
                else:
                    retained.append(lead)
            if not removed_ids:
                return []
            state["leads"] = retained
            for lead_id in removed_ids:
                state["logs"].append(self._event("lead_purged", lead_id, "Lead removed by retention policy", now))
            self._atomic_write_state(state)
            return removed_ids

    def export_leads_csv(self) -> str:
        fields = [
            "id", "received_at", "source", "name", "email", "phone", "company", "owner", "service_needed",
            "priority_label", "priority_score", "pipeline_stage", "follow_up_date", "status",
            "next_action", "suggested_reply", "ai_summary", "analysis_mode",
        ]
        output = StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\r\n")
        writer.writeheader()
        for lead in self.list_leads():
            writer.writerow({field: csv_safe(lead.get(field, "")) for field in fields})
        return output.getvalue()

    def reset(self) -> None:
        with self._state_lock(exclusive=True):
            self._atomic_write_state({"schema_version": self.SCHEMA_VERSION, "leads": [], "logs": []})


def csv_safe(value: object) -> object:
    if not isinstance(value, str):
        return value
    if value.startswith(("\t", "\r")) or value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value
