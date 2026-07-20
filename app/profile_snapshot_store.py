from __future__ import annotations

from supabase import Client, create_client

from app.settings import Settings


def create_supabase_client(
    settings: Settings,
) -> Client:
    return create_client(
        settings.supabase_url,
        settings.supabase_secret_key,
    )


def save_profile_snapshot(
    settings: Settings,
    result: dict,
) -> int:
    client = create_supabase_client(settings)

    payload = {
        "source_id": result["source_id"],
        "scraped_at": result["scraped_at"],
        "profile_data": result.get(
            "profile",
            {},
        ),
        "experience_raw_text": result.get(
            "experience_raw_text",
            "",
        )
        or None,
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

    snapshot_id = response.data[0].get("id")

    if snapshot_id is None:
        raise RuntimeError(
            "Inserted snapshot has no id."
        )

    return int(snapshot_id)
