"""Remove locally stored leads older than the configured retention period."""

from app import build_store
from config import Settings


def main() -> None:
    settings = Settings.from_env()
    removed = build_store(settings).purge_expired()
    print(f"Purged {len(removed)} lead(s) older than {settings.contact_retention_days} days.")


if __name__ == "__main__":
    main()
