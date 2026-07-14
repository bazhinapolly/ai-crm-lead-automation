"""Lead analysis layer for the AI CRM Lead Automation demo.

The default implementation is deterministic so the portfolio demo can be
verified without external API keys. A real client version can replace
`analyze_lead` with an OpenAI/Claude/Gemini call that returns the same schema.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, asdict


SERVICE_KEYWORDS = {
    "crm_automation": ["crm", "hubspot", "pipedrive", "gohighlevel", "lead routing"],
    "google_workspace": ["gmail", "google sheets", "workspace", "spreadsheet", "drive"],
    "support_chatbot": ["chatbot", "faq", "customer support", "support"],
    "appointment_automation": ["appointment", "reminder", "booking", "calendar"],
    "invoice_po_tracking": ["invoice", "po", "payment", "billing"],
    "reporting_dashboard": ["dashboard", "report", "weekly", "analytics"],
}

URGENT_WORDS = ["urgent", "tomorrow", "asap", "this week", "start this month", "quickly"]
BUDGET_WORDS = ["budget", "$", "usd", "around", "pricing"]
LOW_BUDGET_WORDS = ["low budget", "$100", "cheap", "lowest"]
HIGH_INTENT_WORDS = ["need", "want", "trying to start", "can start", "ready", "please call"]


@dataclass
class LeadAnalysis:
    lead_type: str
    service_needed: str
    urgency: str
    budget_signal: str
    intent: str
    priority_score: int
    priority_label: str
    pipeline_stage: str
    follow_up_date: str
    next_action: str
    ai_summary: str
    suggested_reply: str


def analyze_lead(message: str, received_at: dt.datetime | None = None) -> LeadAnalysis:
    """Return structured lead analysis for a raw inquiry message."""
    received_at = received_at or dt.datetime.now(dt.timezone.utc)
    text = " ".join(message.strip().split())
    lowered = text.lower()

    service_needed = detect_service(lowered)
    urgency = detect_urgency(lowered)
    budget_signal = detect_budget(lowered)
    intent = detect_intent(lowered)
    priority_score = score_lead(urgency, budget_signal, intent, service_needed)
    priority_label = label_priority(priority_score)
    pipeline_stage = stage_for_priority(priority_label)
    follow_up_date = calculate_follow_up_date(received_at, priority_label)
    lead_type = "inbound_lead" if intent != "low_intent" else "research_inquiry"
    next_action = next_action_for_priority(priority_label, service_needed)
    summary = build_summary(text, service_needed, urgency, budget_signal)
    reply = build_suggested_reply(service_needed, urgency)

    return LeadAnalysis(
        lead_type=lead_type,
        service_needed=service_needed,
        urgency=urgency,
        budget_signal=budget_signal,
        intent=intent,
        priority_score=priority_score,
        priority_label=priority_label,
        pipeline_stage=pipeline_stage,
        follow_up_date=follow_up_date,
        next_action=next_action,
        ai_summary=summary,
        suggested_reply=reply,
    )


def extract_contact(message: str) -> dict:
    """Extract lightweight contact details from a message."""
    email_match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", message)
    phone_match = re.search(r"(\+?\d[\d\s().-]{7,}\d)", message)
    name = extract_name(message)
    company = extract_company(message)

    return {
        "name": name,
        "email": email_match.group(0) if email_match else "",
        "phone": phone_match.group(0).strip() if phone_match else "",
        "company": company,
    }


def detect_service(lowered: str) -> str:
    scores = {
        service: sum(1 for keyword in keywords if keyword in lowered)
        for service, keywords in SERVICE_KEYWORDS.items()
    }
    service, score = max(scores.items(), key=lambda item: item[1])
    return service if score else "general_automation"


def detect_urgency(lowered: str) -> str:
    if any(word in lowered for word in ["tomorrow", "asap", "urgent"]):
        return "high"
    if any(word in lowered for word in URGENT_WORDS):
        return "medium"
    return "normal"


def detect_budget(lowered: str) -> str:
    if any(word in lowered for word in LOW_BUDGET_WORDS):
        return "low_budget"
    if any(word in lowered for word in BUDGET_WORDS):
        return "budget_mentioned"
    return "unknown"


def detect_intent(lowered: str) -> str:
    if "curious" in lowered or "researching" in lowered:
        return "medium_intent"
    if any(word in lowered for word in HIGH_INTENT_WORDS):
        return "high_intent"
    return "low_intent"


def score_lead(urgency: str, budget_signal: str, intent: str, service_needed: str) -> int:
    score = 35
    score += {"high": 25, "medium": 15, "normal": 5}.get(urgency, 0)
    score += {"budget_mentioned": 15, "unknown": 5, "low_budget": -10}.get(budget_signal, 0)
    score += {"high_intent": 25, "medium_intent": 10, "low_intent": 0}.get(intent, 0)
    if service_needed in {"crm_automation", "google_workspace", "appointment_automation"}:
        score += 10
    return max(0, min(score, 100))


def label_priority(score: int) -> str:
    if score >= 75:
        return "Hot"
    if score >= 50:
        return "Warm"
    return "Cold"


def stage_for_priority(priority_label: str) -> str:
    return {"Hot": "Contact Today", "Warm": "Qualified", "Cold": "Nurture"}.get(
        priority_label, "New"
    )


def calculate_follow_up_date(received_at: dt.datetime, priority_label: str) -> str:
    days = {"Hot": 0, "Warm": 2, "Cold": 7}.get(priority_label, 3)
    return (received_at + dt.timedelta(days=days)).date().isoformat()


def next_action_for_priority(priority_label: str, service_needed: str) -> str:
    if priority_label == "Hot":
        return f"Reply today and offer a short discovery call about {service_needed}."
    if priority_label == "Warm":
        return f"Send a helpful reply and ask 2-3 qualification questions about {service_needed}."
    return "Add to nurture list and send a lightweight overview."


def build_summary(text: str, service_needed: str, urgency: str, budget_signal: str) -> str:
    preview = text[:160] + ("..." if len(text) > 160 else "")
    return (
        f"Lead is asking about {service_needed}. "
        f"Urgency: {urgency}. Budget signal: {budget_signal}. "
        f"Message preview: {preview}"
    )


def build_suggested_reply(service_needed: str, urgency: str) -> str:
    timing = "today" if urgency == "high" else "this week"
    return (
        "Thanks for reaching out. I can help with this workflow. "
        f"The best next step is a short call {timing} to confirm your current tools, "
        f"the desired {service_needed} process, and the follow-up rules before implementation."
    )


def extract_name(message: str) -> str:
    patterns = [
        r"(?:my name is|i am|i'm|this is)\s+([A-Z][a-z]+(?:\s+(?!from\b|at\b|email\b)[A-Z][a-z]+)?)",
        r"Contact:\s*([A-Z][a-z]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def extract_company(message: str) -> str:
    patterns = [
        r"from\s+([A-Z][A-Za-z0-9&\s.-]{2,40})(?:\.|,|\swe|\swant|\sneed)",
        r"at\s+([A-Z][A-Za-z0-9&\s.-]{2,40})(?:\.|,|\swe|\swant|\sneed)",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def analysis_to_dict(analysis: LeadAnalysis) -> dict:
    return asdict(analysis)
