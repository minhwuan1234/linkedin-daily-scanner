from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(
    dotenv_path=ENV_FILE,
    override=False,
)


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_secret_key: str
    google_sheet_id: str
    google_service_account_json: str

    linkedin_worker_idle_poll_seconds: int
    linkedin_worker_error_retry_seconds: int


def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )

    return value


def get_positive_int_env(
    name: str,
    default: int,
) -> int:
    raw_value = os.getenv(
        name,
        str(default),
    ).strip()

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(
            f"{name} must be an integer. "
            f"Received: {raw_value!r}"
        ) from exc

    if value <= 0:
        raise RuntimeError(
            f"{name} must be greater than 0. "
            f"Received: {value}"
        )

    return value


def load_settings() -> Settings:
    return Settings(
        supabase_url=get_required_env(
            "SUPABASE_URL"
        ),
        supabase_secret_key=get_required_env(
            "SUPABASE_SECRET_KEY"
        ),
        google_sheet_id=get_required_env(
            "GOOGLE_SHEET_ID"
        ),
        google_service_account_json=get_required_env(
            "GOOGLE_SERVICE_ACCOUNT_JSON"
        ),
        linkedin_worker_idle_poll_seconds=(
            get_positive_int_env(
                "LINKEDIN_WORKER_IDLE_POLL_SECONDS",
                3,
            )
        ),
        linkedin_worker_error_retry_seconds=(
            get_positive_int_env(
                "LINKEDIN_WORKER_ERROR_RETRY_SECONDS",
                10,
            )
        ),
    )
