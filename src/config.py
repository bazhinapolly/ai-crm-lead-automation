"""Validated environment configuration for the local CRM application."""

from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def _bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name, "1" if default else "0").strip().lower()
    if value not in {"0", "1", "false", "true", "no", "yes"}:
        raise ValueError(f"{name} must be 0 or 1")
    return value in {"1", "true", "yes"}


def _int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8080
    data_dir: Path = ROOT_DIR / "data"
    max_request_bytes: int = 16_384
    max_message_chars: int = 10_000
    store_raw_message: bool = False
    use_openai: bool = False
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini-2024-07-18"
    openai_timeout_seconds: int = 20
    local_api_key: str = ""
    contact_retention_days: int = 90
    session_ttl_seconds: int = 3600
    login_failure_window_seconds: int = 60
    login_failure_max: int = 5
    intake_rate_limit_window_seconds: int = 60
    intake_rate_limit_max: int = 30
    intake_rate_limit_max_buckets: int = 1024
    openai_max_concurrency: int = 2

    @classmethod
    def from_env(cls) -> "Settings":
        host = os.environ.get("HOST", "127.0.0.1").strip()
        try:
            if not ipaddress.ip_address(host).is_loopback:
                raise ValueError("HOST must be a loopback address for this local application")
        except ValueError as exc:
            if "loopback" in str(exc):
                raise
            raise ValueError("HOST must be a numeric loopback address") from exc
        use_openai = _bool("USE_OPENAI")
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini-2024-07-18").strip()
        if use_openai and not key:
            raise ValueError("OPENAI_API_KEY is required when USE_OPENAI=1")
        if use_openai and not model:
            raise ValueError("OPENAI_MODEL is required when USE_OPENAI=1")
        data_value = os.environ.get("CRM_DATA_DIR", "").strip()
        local_api_key = os.environ.get("LOCAL_API_KEY", "").strip()
        if local_api_key and len(local_api_key) < 32:
            raise ValueError("LOCAL_API_KEY must contain at least 32 characters")
        return cls(
            host=host,
            port=_int("PORT", 8080, 1, 65_535),
            data_dir=Path(data_value).expanduser().resolve() if data_value else ROOT_DIR / "data",
            max_request_bytes=_int("MAX_REQUEST_BYTES", 16_384, 1_024, 1_048_576),
            max_message_chars=_int("MAX_MESSAGE_CHARS", 10_000, 100, 100_000),
            store_raw_message=_bool("STORE_RAW_MESSAGE"),
            use_openai=use_openai,
            openai_api_key=key,
            openai_model=model,
            openai_timeout_seconds=_int("OPENAI_TIMEOUT_SECONDS", 20, 1, 120),
            local_api_key=local_api_key,
            contact_retention_days=_int("CONTACT_RETENTION_DAYS", 90, 1, 3650),
            session_ttl_seconds=_int("SESSION_TTL_SECONDS", 3600, 1, 86400),
            login_failure_window_seconds=_int("LOGIN_FAILURE_WINDOW_SECONDS", 60, 1, 3600),
            login_failure_max=_int("LOGIN_FAILURE_MAX", 5, 1, 100),
            intake_rate_limit_window_seconds=_int("INTAKE_RATE_LIMIT_WINDOW_SECONDS", 60, 1, 3600),
            intake_rate_limit_max=_int("INTAKE_RATE_LIMIT_MAX", 30, 1, 1000),
            intake_rate_limit_max_buckets=_int("INTAKE_RATE_LIMIT_MAX_BUCKETS", 1024, 1, 10000),
            openai_max_concurrency=_int("OPENAI_MAX_CONCURRENCY", 2, 1, 20),
        )
