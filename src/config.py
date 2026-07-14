"""Validated environment configuration for the local reference application."""

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

    @classmethod
    def from_env(cls) -> "Settings":
        host = os.environ.get("HOST", "127.0.0.1").strip()
        try:
            if not ipaddress.ip_address(host).is_loopback:
                raise ValueError("HOST must be a loopback address for this local reference app")
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
        )
