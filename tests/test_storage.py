from __future__ import annotations

import csv
import datetime as dt
import json
import tempfile
import threading
import unittest
from io import StringIO
from pathlib import Path

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
        self.assertTrue(self.store.leads_file.exists())
        self.assertTrue(self.store.logs_file.exists())

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

    def test_csv_export_neutralizes_formulas(self) -> None:
        lead = self.store.create_lead("form", "This is =HYPERLINK from Safe Co. Need CRM", NOW)
        records = json.loads(self.store.leads_file.read_text())
        records[0]["name"] = " =2+3"
        self.store._atomic_write(self.store.leads_file, records)
        rows = list(csv.DictReader(StringIO(self.store.export_leads_csv())))
        self.assertEqual(rows[0]["name"], "' =2+3")

    def test_corrupt_json_raises_safe_storage_error(self) -> None:
        self.store.leads_file.write_text("not-json", encoding="utf-8")
        with self.assertRaisesRegex(DataStoreError, "leads.json"):
            self.store.list_leads()

    def test_wrong_json_shape_is_rejected(self) -> None:
        self.store.leads_file.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(DataStoreError, "list of objects"):
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


if __name__ == "__main__":
    unittest.main()
