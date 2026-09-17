from __future__ import annotations

from urllib.parse import urlparse

from supabase import Client, create_client

from app.google_sheets import LinkedInSource
from app.settings import Settings


def create_supabase_client(settings: Settings) -> Client:
    return create_client(
        settings.supabase_url,
        settings.supabase_secret_key,
    )


def detect_source_type(linkedin_url: str) -> str:
    path = urlparse(linkedin_url).path.lower()

    if path.startswith("/in/"):
        return "profile"

    if path.startswith("/company/"):
        return "company"

    raise ValueError(
        f"Unsupported LinkedIn URL: {linkedin_url}"
    )


def source_to_payload(source: LinkedInSource) -> dict:
    return {
        "name": source.name,
        "email_1": source.email_1 or None,
        "email_2": source.email_2 or None,
        "role": source.role or None,
        "company": source.company or None,
        "linkedin_url": source.linkedin_url,
        "source_type": detect_source_type(
            source.linkedin_url
        ),
        "description": source.description or None,
        "coaching_available": (
            source.coaching_available or None
        ),
        "coaching_method": (
            source.coaching_method or None
        ),
        "coaching_language": (
            source.coaching_language or None
        ),
        "coaching": source.coaching or None,
        "location": source.location or None,
        "enabled": True,
    }


def sync_sources_to_supabase(
    settings: Settings,
    sources: list[LinkedInSource],
    table_name: str = "linkedin_sources",
    batch_size: int = 200,
) -> int:
    if not sources:
        return 0

    client = create_supabase_client(settings)

    payloads = [
        source_to_payload(source)
        for source in sources
    ]

    synced_count = 0

    for start in range(0, len(payloads), batch_size):
        batch = payloads[start:start + batch_size]

        response = (
            client.table(table_name)
            .upsert(
                batch,
                on_conflict="linkedin_url",
            )
            .execute()
        )

        if response.data is None:
            raise RuntimeError(
                "Supabase did not return data after upsert."
            )

        synced_count += len(batch)

    return synced_count
