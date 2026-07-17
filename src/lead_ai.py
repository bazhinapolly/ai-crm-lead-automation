"""Deterministic lead analysis with an optional structured AI provider."""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
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
SCORING_POLICY_PATH = Path(__file__).resolve().parents[1] / "config" / "scoring-policy.json"
EMAIL_PATTERN = re.compile(
    r"(?<![A-Za-z0-9.!#$%&'*+/=?^_`{|}~-])"
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"[A-Za-z]{2,63}(?![A-Za-z0-9-])"
)


def load_scoring_policy(path: Path = SCORING_POLICY_PATH) -> dict[str, object]:
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("scoring policy must be readable JSON") from exc
    required = {"base_score", "urgency", "budget_signal", "intent", "service_bonus", "priority_thresholds"}
    if not isinstance(policy, dict) or set(policy) != required:
        raise ValueError("scoring policy has an invalid schema")
    if not _is_policy_integer(policy["base_score"]):
        raise ValueError("scoring policy base_score must be an integer")
    for field, expected_keys in (
        ("urgency", URGENCY_VALUES),
        ("budget_signal", BUDGET_VALUES),
        ("intent", INTENT_VALUES),
    ):
        values = policy.get(field)
        if (
            not isinstance(values, dict)
            or set(values) != set(expected_keys)
            or not all(_is_policy_integer(item) for item in values.values())
        ):
            raise ValueError(f"scoring policy {field} weights are invalid")
    service_bonus = policy.get("service_bonus")
    if not isinstance(service_bonus, dict) or set(service_bonus) != {"points", "services"}:
        raise ValueError("scoring policy service_bonus is invalid")
    services = service_bonus.get("services")
    if (
        not _is_policy_integer(service_bonus.get("points"))
        or not isinstance(services, list)
        or not services
        or any(not isinstance(service, str) or service not in SERVICE_VALUES for service in services)
        or len(set(services)) != len(services)
    ):
        raise ValueError("scoring policy service_bonus is invalid")
    thresholds = policy.get("priority_thresholds")
    if not isinstance(thresholds, dict) or set(thresholds) != {"hot", "warm"}:
        raise ValueError("scoring policy thresholds are invalid")
    if not all(_is_policy_integer(value) for value in thresholds.values()) or not 0 <= thresholds["warm"] < thresholds["hot"] <= 100:
        raise ValueError("scoring policy thresholds must be ordered integers from 0 to 100")
    return policy


def _is_policy_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and -100 <= value <= 100


SCORING_POLICY = load_scoring_policy()


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
    summary = build_summary(**{key: values[key] for key in ("service_needed", "urgency", "budget_signal")})
    reply = build_suggested_reply(values["service_needed"], values["urgency"])

    if provider is not None:
        contact = extract_contact(text)
        provider_input = redact_sensitive_text(text, contact.values())
        provided = validate_provider_analysis(provider.analyze(provider_input), contact.values())
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


def validate_provider_analysis(value: object, sensitive_values: object = ()) -> dict[str, str]:
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
        clean[key] = redact_sensitive_text(" ".join(item.split()), sensitive_values)
    return clean


def redact_sensitive_text(value: str, sensitive_values: object = ()) -> str:
    """Best-effort local PII removal for provider input and generated fields."""
    text = " ".join(value.split())
    for item in sorted({str(item).strip() for item in sensitive_values if str(item).strip()}, key=len, reverse=True):
        text = re.sub(re.escape(item), "[redacted]", text, flags=re.IGNORECASE)
    text = EMAIL_PATTERN.sub("[email]", text)
    text = re.sub(r"(?<!\w)\+?\d(?:[\d\s().-]{6,}\d)(?!\w)", "[phone]", text)
    def redact_long_number(match: re.Match[str]) -> str:
        return "[long-number]" if sum(character.isdigit() for character in match.group(0)) >= 8 else match.group(0)
    return re.sub(r"(?<!\w)\d[\d\s.-]{6,}\d(?!\w)", redact_long_number, text)


def extract_contact(message: str) -> dict[str, str]:
    email = EMAIL_PATTERN.search(message)
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
    score = int(SCORING_POLICY["base_score"])
    score += int(SCORING_POLICY["urgency"][urgency])
    score += int(SCORING_POLICY["budget_signal"][budget_signal])
    score += int(SCORING_POLICY["intent"][intent])
    service_bonus = SCORING_POLICY["service_bonus"]
    if service_needed in set(service_bonus["services"]): score += int(service_bonus["points"])
    return min(100, max(0, score))


def label_priority(score: int) -> str:
    thresholds = SCORING_POLICY["priority_thresholds"]
    return "Hot" if score >= thresholds["hot"] else "Warm" if score >= thresholds["warm"] else "Cold"


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


def build_summary(service_needed: str, urgency: str, budget_signal: str) -> str:
    return f"Lead asks about {service_needed}. Urgency: {urgency}. Budget: {budget_signal}."


def build_suggested_reply(service: str, urgency: str) -> str:
    timing = "today" if urgency == "high" else "this week"
    return (
        "Thanks for reaching out. I can help with this workflow. "
        f"The next step is a short call {timing} to confirm your tools, the {service} process, and follow-up rules."
    )


def extract_name(message: str) -> str:
    for pattern in (
        r"(?:My name is|I am|I'm|This is)\s+([A-Z][A-Za-z'-]{1,30}(?:\s+(?!from\b|at\b)[A-Z][A-Za-z'-]{1,30})?)",
        r"(?:Contact|contact)\s*:\s*([A-Z][A-Za-z'-]{1,30})",
    ):
        match = re.search(pattern, message)
        if match:
            return match.group(1).strip()
    return ""


def extract_company(message: str) -> str:
    for pattern in (
        r"(?:from|at)\s+([A-Z][A-Za-z0-9&'. -]{1,39}?)(?=[.,]|\s+(?:we|i|need|want|email)\b|$)",
    ):
        match = re.search(pattern, message)
        if match:
            return match.group(1).strip()
    return ""


def analysis_to_dict(analysis: LeadAnalysis) -> dict[str, object]:
    return asdict(analysis)
