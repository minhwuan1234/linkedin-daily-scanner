from __future__ import annotations

from typing import Any

from supabase import Client, create_client

from app.settings import Settings


def create_supabase_client(
    settings: Settings,
) -> Client:
    return create_client(
        settings.supabase_url,
        settings.supabase_secret_key,
    )


def normalize_optional_text(
    value: Any,
) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip()

    return normalized or None


def save_profile_snapshot(
    settings: Settings,
    result: dict,
) -> int:
    client = create_supabase_client(settings)

    profile = result.get(
        "profile",
        {},
    )

    payload = {
        "source_id": result["source_id"],
        "scraped_at": result["scraped_at"],

        "name": normalize_optional_text(
            profile.get("name")
        ),
        "linkedin_url": normalize_optional_text(
            profile.get("linkedin_url")
        ),
        "headline": normalize_optional_text(
            profile.get("headline")
        ),
        "location": normalize_optional_text(
            profile.get("location")
        ),
        "followers_count_text": normalize_optional_text(
            profile.get("followers_count_text")
        ),
        "connections_count_text": normalize_optional_text(
            profile.get("connections_count_text")
        ),
        "about_text": normalize_optional_text(
            profile.get("about_text")
        ),

        "experience_raw_text": normalize_optional_text(
            result.get("experience_raw_text")
        ),

        # Giữ nguyên toàn bộ profile object
        # để debug hoặc xử lý lại sau này.
        "raw_profile_data": profile,

        "errors": result.get(
            "errors",
            [],
        ),
    }

    response = (
        client.table(
            "linkedin_profile_snapshots"
        )
        .insert(payload)
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            "Supabase did not return the "
            "inserted profile snapshot."
        )

    snapshot_id = response.data[0].get(
        "id"
    )

    if snapshot_id is None:
        raise RuntimeError(
            "Inserted snapshot has no id."
        )

    return int(snapshot_id)
