from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_secret_key: str
    google_sheet_id: str
    google_service_account_json: str


def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )

    return value


def load_settings() -> Settings:
    return Settings(
        supabase_url=get_required_env("SUPABASE_URL"),
        supabase_secret_key=get_required_env(
            "SUPABASE_SECRET_KEY"
        ),
        google_sheet_id=get_required_env("GOOGLE_SHEET_ID"),
        google_service_account_json=get_required_env(
            "GOOGLE_SERVICE_ACCOUNT_JSON"
        ),
    )
