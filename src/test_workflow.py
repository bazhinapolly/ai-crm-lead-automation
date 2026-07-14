"""Small verification tests for the portfolio demo."""

from __future__ import annotations

import datetime as dt

from lead_ai import analyze_lead, extract_contact
from storage import create_lead, list_leads, pipeline_metrics, reset_demo_data


def test_analysis_hot_lead() -> None:
    message = (
        "Hi, my name is Sarah from Oakwood Dental. We need appointment "
        "automation urgently this week. Budget is around $1500."
    )
    analysis = analyze_lead(message, dt.datetime(2026, 7, 2, tzinfo=dt.timezone.utc))
    assert analysis.priority_label == "Hot"
    assert analysis.service_needed == "appointment_automation"
    assert analysis.pipeline_stage == "Contact Today"


def test_contact_extraction() -> None:
    contact = extract_contact("This is Mark from BrightRoof. Email mark@example.com")
    assert contact["name"] == "Mark"
    assert contact["email"] == "mark@example.com"


def test_storage_workflow() -> None:
    reset_demo_data()
    lead = create_lead("website_form", "Need CRM automation ASAP. Email me at ops@example.com")
    leads = list_leads()
    metrics = pipeline_metrics()
    assert lead["id"]
    assert len(leads) == 1
    assert metrics["total_leads"] == 1


def main() -> None:
    test_analysis_hot_lead()
    test_contact_extraction()
    test_storage_workflow()
    print("All workflow tests passed.")


if __name__ == "__main__":
    main()

