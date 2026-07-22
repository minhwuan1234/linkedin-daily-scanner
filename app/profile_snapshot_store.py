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


def normalize_recent_post_captions(
    value: Any,
) -> list[str]:
    if not isinstance(value, list):
        return []

    captions: list[str] = []

    for item in value:
        caption = normalize_optional_text(
            item
        )

        if caption is None:
            continue

        captions.append(caption)

        if len(captions) >= 5:
            break

    return captions


def build_post_caption_fields(
    captions: list[str],
) -> dict[str, str | None]:
    return {
        "post_1_caption": (
            captions[0]
            if len(captions) >= 1
            else None
        ),
        "post_2_caption": (
            captions[1]
            if len(captions) >= 2
            else None
        ),
        "post_3_caption": (
            captions[2]
            if len(captions) >= 3
            else None
        ),
        "post_4_caption": (
            captions[3]
            if len(captions) >= 4
            else None
        ),
        "post_5_caption": (
            captions[4]
            if len(captions) >= 5
            else None
        ),
    }


def save_profile_snapshot(
    settings: Settings,
    result: dict,
) -> int:
    client = create_supabase_client(
        settings
    )

    profile = result.get(
        "profile",
        {},
    )

    if not isinstance(profile, dict):
        profile = {}

    errors = result.get(
        "errors",
        [],
    )

    if not isinstance(errors, list):
        errors = []

    recent_post_captions = (
        normalize_recent_post_captions(
            result.get(
                "recent_post_captions",
                [],
            )
        )
    )

    post_caption_fields = (
        build_post_caption_fields(
            recent_post_captions
        )
    )

    payload = {
        "source_id": result["source_id"],
        "scraped_at": result["scraped_at"],

        # Giữ cột cũ để tương thích schema hiện tại.
        "profile_data": profile,

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
        "followers_count_text": (
            normalize_optional_text(
                profile.get(
                    "followers_count_text"
                )
            )
        ),
        "connections_count_text": (
            normalize_optional_text(
                profile.get(
                    "connections_count_text"
                )
            )
        ),
        "about_text": normalize_optional_text(
            profile.get("about_text")
        ),
        "experience_raw_text": (
            normalize_optional_text(
                result.get(
                    "experience_raw_text"
                )
            )
        ),

        "post_1_caption": (
            post_caption_fields[
                "post_1_caption"
            ]
        ),
        "post_2_caption": (
            post_caption_fields[
                "post_2_caption"
            ]
        ),
        "post_3_caption": (
            post_caption_fields[
                "post_3_caption"
            ]
        ),
        "post_4_caption": (
            post_caption_fields[
                "post_4_caption"
            ]
        ),
        "post_5_caption": (
            post_caption_fields[
                "post_5_caption"
            ]
        ),

        # Lưu toàn bộ kết quả scraper để debug.
        "raw_profile_data": result,

        "errors": errors,
    }

    print("")
    print("Supabase snapshot payload:")
    print(
        f"Source ID: {payload['source_id']}"
    )
    print(
        f"Name: {payload['name']}"
    )
    print(
        f"LinkedIn URL: "
        f"{payload['linkedin_url']}"
    )
    print(
        "Experience length: "
        f"{len(payload['experience_raw_text'] or '')}"
    )
    print(
        "Recent post captions: "
        f"{len(recent_post_captions)}"
    )

    for index in range(1, 6):
        field_name = (
            f"post_{index}_caption"
        )

        caption = payload[
            field_name
        ]

        print(
            f"{field_name}: "
            f"{'yes' if caption else 'null'}"
        )

    response = (
        client.table(
            "linkedin_profile_snapshots"
        )
        .insert(payload)
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            "Supabase insert returned no data."
        )

    inserted_row = response.data[0]

    snapshot_id = inserted_row.get(
        "id"
    )

    if snapshot_id is None:
        raise RuntimeError(
            "Inserted snapshot has no id."
        )

    return int(snapshot_id)


def mark_source_scanned(
    settings: Settings,
    source_id: int,
    scanned_at: str,
) -> None:
    client = create_supabase_client(
        settings
    )

    response = (
        client.table(
            "linkedin_sources"
        )
        .update(
            {
                "last_scanned_at": scanned_at,
            }
        )
        .eq(
            "id",
            source_id,
        )
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            "Failed to update "
            "last_scanned_at "
            f"for source {source_id}."
        )
