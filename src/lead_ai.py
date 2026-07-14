"""Deterministic lead analysis with an optional structured AI provider."""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import asdict, dataclass
from typing import Protocol


SERVICES = {
    "crm_automation": ("crm", "hubspot", "pipedrive", "gohighlevel", "lead routing"),
    "google_workspace": ("gmail", "google sheets", "workspace", "spreadsheet", "drive"),
    "support_chatbot": ("chatbot", "faq", "customer support", "support"),
    "appointment_automation": ("appointment", "reminder", "booking", "calendar"),
    "invoice_po_tracking": ("invoice", "purchase order", "payment", "billing"),
    "reporting_dashboard": ("dashboard", "reporting", "analytics", "weekly report"),
}
SERVICE_VALUES = frozenset((*SERVICES, "general_automation"))
URGENCY_VALUES = frozenset(("high", "medium", "normal"))
BUDGET_VALUES = frozenset(("budget_mentioned", "low_budget", "unknown"))
INTENT_VALUES = frozenset(("high_intent", "medium_intent", "low_intent"))
PROVIDER_KEYS = frozenset(
    ("service_needed", "urgency", "budget_signal", "intent", "ai_summary", "suggested_reply")
)


class AnalysisProvider(Protocol):
    def analyze(self, message: str) -> dict[str, object]: ...


@dataclass(frozen=True)
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
    analysis_mode: str


def analyze_lead(
    message: str,
    received_at: dt.datetime | None = None,
    provider: AnalysisProvider | None = None,
) -> LeadAnalysis:
    """Analyze one normalized, non-empty message into a bounded CRM schema."""
    text = " ".join(message.strip().split())
    if not text:
        raise ValueError("message is required")
    received_at = received_at or dt.datetime.now(dt.timezone.utc)
    lowered = text.casefold()

    values: dict[str, str] = {
        "service_needed": detect_service(lowered),
        "urgency": detect_urgency(lowered),
        "budget_signal": detect_budget(lowered),
        "intent": detect_intent(lowered),
    }
    mode = "deterministic"
    summary = build_summary(text, **{key: values[key] for key in ("service_needed", "urgency", "budget_signal")})
    reply = build_suggested_reply(values["service_needed"], values["urgency"])

    if provider is not None:
        provided = validate_provider_analysis(provider.analyze(text))
        values.update({key: provided[key] for key in ("service_needed", "urgency", "budget_signal", "intent")})
        summary = provided["ai_summary"]
        reply = provided["suggested_reply"]
        mode = "openai"

    score = score_lead(**values)
    label = label_priority(score)
    return LeadAnalysis(
        lead_type="inbound_lead" if values["intent"] != "low_intent" else "research_inquiry",
        priority_score=score,
        priority_label=label,
        pipeline_stage=stage_for_priority(label),
        follow_up_date=calculate_follow_up_date(received_at, label),
        next_action=next_action_for_priority(label, values["service_needed"]),
        ai_summary=summary,
        suggested_reply=reply,
        analysis_mode=mode,
        **values,
    )


def validate_provider_analysis(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != PROVIDER_KEYS:
        raise ValueError("AI provider returned an invalid analysis schema")
    enum_fields = {
        "service_needed": SERVICE_VALUES,
        "urgency": URGENCY_VALUES,
        "budget_signal": BUDGET_VALUES,
        "intent": INTENT_VALUES,
    }
    clean: dict[str, str] = {}
    for key, allowed in enum_fields.items():
        item = value.get(key)
        if not isinstance(item, str) or item not in allowed:
            raise ValueError("AI provider returned an invalid analysis value")
        clean[key] = item
    for key, limit in (("ai_summary", 600), ("suggested_reply", 1200)):
        item = value.get(key)
        if not isinstance(item, str) or not item.strip() or len(item) > limit:
            raise ValueError("AI provider returned invalid generated text")
        clean[key] = " ".join(item.split())
    return clean


def extract_contact(message: str) -> dict[str, str]:
    email = re.search(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])", message)
    phone = re.search(r"(?<!\w)(\+?\d(?:[\d\s().-]{6,}\d))(?!\w)", message)
    return {
        "name": extract_name(message),
        "email": email.group(0) if email else "",
        "phone": phone.group(1).strip() if phone else "",
        "company": extract_company(message),
    }


def detect_service(lowered: str) -> str:
    scores = {service: sum(keyword in lowered for keyword in keywords) for service, keywords in SERVICES.items()}
    service, score = max(scores.items(), key=lambda item: item[1])
    return service if score else "general_automation"


def detect_urgency(lowered: str) -> str:
    if any(word in lowered for word in ("tomorrow", "asap", "urgent", "immediately")):
        return "high"
    if any(word in lowered for word in ("this week", "this month", "quickly", "soon")):
        return "medium"
    return "normal"


def detect_budget(lowered: str) -> str:
    if any(word in lowered for word in ("low budget", "cheap", "lowest price")):
        return "low_budget"
    if re.search(r"(?:[$€£]\s?\d|\d[\d,.]*\s?(?:usd|eur|gbp|dollars?))", lowered) or "budget" in lowered:
        return "budget_mentioned"
    return "unknown"


def detect_intent(lowered: str) -> str:
    if any(word in lowered for word in ("just curious", "researching", "information only")):
        return "medium_intent"
    if any(word in lowered for word in ("need", "want", "ready", "please call", "can start", "quote")):
        return "high_intent"
    return "low_intent"


def score_lead(urgency: str, budget_signal: str, intent: str, service_needed: str) -> int:
    score = 35
    score += {"high": 25, "medium": 15, "normal": 5}[urgency]
    score += {"budget_mentioned": 15, "unknown": 5, "low_budget": -10}[budget_signal]
    score += {"high_intent": 25, "medium_intent": 10, "low_intent": 0}[intent]
    if service_needed in {"crm_automation", "google_workspace", "appointment_automation"}:
        score += 10
    return min(100, max(0, score))


def label_priority(score: int) -> str:
    return "Hot" if score >= 75 else "Warm" if score >= 50 else "Cold"


def stage_for_priority(label: str) -> str:
    return {"Hot": "Contact Today", "Warm": "Qualified", "Cold": "Nurture"}[label]


def calculate_follow_up_date(received_at: dt.datetime, label: str) -> str:
    return (received_at + dt.timedelta(days={"Hot": 0, "Warm": 2, "Cold": 7}[label])).date().isoformat()


def next_action_for_priority(label: str, service: str) -> str:
    if label == "Hot":
        return f"Reply today and offer a short discovery call about {service}."
    if label == "Warm":
        return f"Send a helpful reply and ask qualification questions about {service}."
    return "Add to the nurture list and send a lightweight overview."


def build_summary(text: str, service_needed: str, urgency: str, budget_signal: str) -> str:
    del text
    return f"Lead asks about {service_needed}. Urgency: {urgency}. Budget: {budget_signal}."


def build_suggested_reply(service: str, urgency: str) -> str:
    timing = "today" if urgency == "high" else "this week"
    return (
        "Thanks for reaching out. I can help with this workflow. "
        f"The next step is a short call {timing} to confirm your tools, the {service} process, and follow-up rules."
    )


def extract_name(message: str) -> str:
    for pattern in (
        r"(?:my name is|i am|i'm|this is)\s+([A-Z][A-Za-z'-]{1,30}(?:\s+(?!from\b|at\b)[A-Z][A-Za-z'-]{1,30})?)",
        r"contact\s*:\s*([A-Z][A-Za-z'-]{1,30})",
    ):
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def extract_company(message: str) -> str:
    for pattern in (
        r"(?:from|at)\s+([A-Z][A-Za-z0-9&'. -]{1,39}?)(?=[.,]|\s+(?:we|i|need|want|email)\b|$)",
    ):
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def analysis_to_dict(analysis: LeadAnalysis) -> dict[str, object]:
    return asdict(analysis)
