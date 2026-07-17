from __future__ import annotations

import csv
import datetime as dt
import json
import tempfile
import threading
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tests import support  # noqa: F401
from storage import DataStoreError, JsonCRM


NOW = dt.datetime(2026, 7, 2, 12, tzinfo=dt.timezone.utc)


class StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.store = JsonCRM(Path(self.temporary.name))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_creates_data_files(self) -> None:
        self.assertTrue(self.store.state_file.exists())

    def test_create_lead_does_not_store_raw_message_by_default(self) -> None:
        lead = self.store.create_lead("website", "Need CRM automation. Email a@example.com", NOW)
        self.assertNotIn("raw_message", lead)
        self.assertEqual(len(self.store.list_logs()), 1)

    def test_raw_message_storage_is_explicit(self) -> None:
        store = JsonCRM(Path(self.temporary.name) / "raw", store_raw_message=True)
        lead = store.create_lead("website", "Need a report", NOW)
        self.assertEqual(lead["raw_message"], "Need a report")

    def test_duplicate_email_marks_second_lead(self) -> None:
        self.store.create_lead("form", "Need CRM. Email Case@Example.com", NOW)
        second = self.store.create_lead("chat", "Need reports. Email case@example.com", NOW)
        self.assertEqual(second["status"], "Duplicate Review")
        self.assertEqual([log["event_type"] for log in self.store.list_logs()].count("duplicate_detected"), 1)

    def test_metrics_are_computed(self) -> None:
        self.store.create_lead("form", "Need CRM urgently. Budget $2000", NOW)
        metrics = self.store.pipeline_metrics()
        self.assertEqual(metrics["total_leads"], 1)
        self.assertEqual(metrics["hot_leads"], 1)
        self.assertEqual(metrics["average_score"], 100)

    def test_follow_up_metrics_use_dates_and_exclude_closed_or_duplicate_records(self) -> None:
        today = dt.date(2026, 7, 10)
        state = json.loads(self.store.state_file.read_text())
        state["leads"] = [
            {"id": "today", "follow_up_date": "2026-07-10", "status": "New"},
            {"id": "late", "follow_up_date": "2026-07-09", "status": "Qualified"},
            {"id": "closed", "follow_up_date": "2026-07-09", "status": "Closed Won"},
            {"id": "duplicate", "follow_up_date": "2026-07-09", "status": "Duplicate Review"},
            {"id": "future", "follow_up_date": "2026-07-11", "status": "New"},
        ]
        self.store._atomic_write_state(state)
        metrics = self.store.pipeline_metrics(today)
        self.assertEqual(metrics["follow_up_today"], 1)
        self.assertEqual(metrics["overdue"], 1)

    def test_csv_export_neutralizes_formulas(self) -> None:
        lead = self.store.create_lead("form", "This is =HYPERLINK from Safe Co. Need CRM", NOW)
        state = json.loads(self.store.state_file.read_text()); state["leads"][0]["name"] = " =2+3"; self.store._atomic_write_state(state)
        rows = list(csv.DictReader(StringIO(self.store.export_leads_csv())))
        self.assertEqual(rows[0]["name"], "' =2+3")
        self.assertIn("phone", rows[0])
        self.assertIn("owner", rows[0])
        self.assertIn("suggested_reply", rows[0])

    def test_export_delete_and_retention_purge_manage_contact_lifecycle(self) -> None:
        old = self.store.create_lead("form", "This is Alice. Need CRM. Email alice@example.com", NOW)
        recent_time = NOW + dt.timedelta(days=100)
        recent = self.store.create_lead("form", "This is Bob. Need reports. Email bob@example.com", recent_time)
        self.assertEqual(self.store.export_lead(old["id"])["email"], "alice@example.com")
        self.assertIsNone(self.store.export_lead("missing"))

        removed = self.store.purge_expired(NOW + dt.timedelta(days=91))
        self.assertEqual(removed, [old["id"]])
        self.assertIsNone(self.store.export_lead(old["id"]))
        self.assertTrue(self.store.delete_lead(recent["id"], recent_time))
        self.assertFalse(self.store.delete_lead("missing", recent_time))
        messages = [item["message"] for item in self.store.list_logs() if item["event_type"] in {"lead_purged", "lead_deleted"}]
        self.assertTrue(messages)
        self.assertFalse(any("alice@" in message or "bob@" in message for message in messages))

    def test_corrupt_json_raises_safe_storage_error(self) -> None:
        self.store.state_file.write_text("not-json", encoding="utf-8")
        with self.assertRaisesRegex(DataStoreError, "crm_state.json"):
            self.store.list_leads()

    def test_wrong_json_shape_is_rejected(self) -> None:
        self.store.state_file.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(DataStoreError, "state schema"):
            self.store.list_leads()

    def test_reset_clears_both_collections(self) -> None:
        self.store.create_lead("form", "Need CRM", NOW)
        self.store.reset()
        self.assertEqual(self.store.list_leads(), [])
        self.assertEqual(self.store.list_logs(), [])

    def test_parallel_creates_do_not_lose_records(self) -> None:
        threads = [threading.Thread(target=self.store.create_lead, args=("test", f"Need CRM {index}")) for index in range(20)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(self.store.list_leads()), 20)
        self.assertEqual(len(self.store.list_logs()), 20)

    def test_lead_and_event_are_committed_in_one_atomic_state_write(self):
        before=self.store.state_file.read_bytes()
        with patch.object(self.store,"_atomic_write_state",side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError,"disk full"): self.store.create_lead("form","Need CRM urgently",NOW)
        self.assertEqual(self.store.state_file.read_bytes(),before); self.assertEqual(self.store.list_leads(),[]); self.assertEqual(self.store.list_logs(),[])

    def test_legacy_collections_are_migrated_to_versioned_state(self):
        directory=Path(self.temporary.name)/"legacy"; directory.mkdir()
        (directory/"leads.json").write_text('[{"id":"lead-1"}]',encoding="utf-8"); (directory/"automation_logs.json").write_text('[{"id":"log-1"}]',encoding="utf-8")
        store=JsonCRM(directory); self.assertEqual(store.list_leads()[0]["id"],"lead-1"); self.assertEqual(store.list_logs()[0]["id"],"log-1"); self.assertEqual(json.loads(store.state_file.read_text())["schema_version"],1)


if __name__ == "__main__":
    unittest.main()
