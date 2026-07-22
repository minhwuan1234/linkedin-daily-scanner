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
        "Recent post captions: "
        f"{len(recent_post_captions)}"
    )

    existing_response = (
        client.table(
            "linkedin_profile_snapshots"
        )
        .select("id")
        .eq(
            "source_id",
            result["source_id"],
        )
        .order(
            "scraped_at",
            desc=True,
        )
        .limit(1)
        .execute()
    )

    if existing_response.data:
        existing_row = (
            existing_response.data[0]
        )

        snapshot_id = existing_row.get(
            "id"
        )

        if snapshot_id is None:
            raise RuntimeError(
                "Existing snapshot has no id."
            )

        response = (
            client.table(
                "linkedin_profile_snapshots"
            )
            .update(payload)
            .eq(
                "id",
                snapshot_id,
            )
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                "Supabase update returned "
                "no data."
            )

        return int(snapshot_id)

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
