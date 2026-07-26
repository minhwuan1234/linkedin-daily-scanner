import logging
import os
from dataclasses import dataclass
from typing import Any

from supabase import Client, create_client


logger = logging.getLogger("supabase-sources")


SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SECRET_KEY = os.getenv(
    "SUPABASE_SECRET_KEY",
    "",
).strip()

TABLE_NAME = "linkedin_sources"
URL_COLUMN = "linkedin_url"


@dataclass(frozen=True)
class SourceInsertResult:
    inserted: list[dict[str, Any]]
    existing_urls: list[str]

    @property
    def inserted_count(self) -> int:
        return len(self.inserted)

    @property
    def existing_count(self) -> int:
        return len(self.existing_urls)


def get_supabase_client() -> Client:
    """
    Tạo Supabase client dùng cho Railway backend.
    """
    if not SUPABASE_URL:
        raise RuntimeError(
            "Missing SUPABASE_URL environment variable"
        )

    if not SUPABASE_SECRET_KEY:
        raise RuntimeError(
            "Missing SUPABASE_SECRET_KEY environment variable"
        )

    return create_client(
        SUPABASE_URL,
        SUPABASE_SECRET_KEY,
    )


def find_existing_urls(
    client: Client,
    urls: list[str],
) -> set[str]:
    """
    Kiểm tra URL nào đã tồn tại trong linkedin_sources.

    Query từng URL để không phụ thuộc cú pháp IN filter
    hoặc unique constraint hiện tại của database.
    """
    existing_urls: set[str] = set()

    for url in urls:
        response = (
            client
            .table(TABLE_NAME)
            .select(URL_COLUMN)
            .eq(URL_COLUMN, url)
            .limit(1)
            .execute()
        )

        if response.data:
            existing_urls.add(url)

    return existing_urls


def insert_new_linkedin_urls(
    urls: list[str],
) -> SourceInsertResult:
    """
    Chỉ insert các LinkedIn URL chưa tồn tại.

    Payload chỉ chứa:
        linkedin_url

    Không update:
        email_1
        email_2
        role
        company
        source_type
        hoặc bất kỳ cột nào khác.
    """
    cleaned_urls: list[str] = []
    seen: set[str] = set()

    for url in urls:
        cleaned_url = str(url or "").strip()

        if not cleaned_url:
            continue

        if cleaned_url in seen:
            continue

        seen.add(cleaned_url)
        cleaned_urls.append(cleaned_url)

    if not cleaned_urls:
        return SourceInsertResult(
            inserted=[],
            existing_urls=[],
        )

    client = get_supabase_client()

    existing_urls = find_existing_urls(
        client=client,
        urls=cleaned_urls,
    )

    new_urls = [
        url
        for url in cleaned_urls
        if url not in existing_urls
    ]

    if not new_urls:
        logger.info(
            "All LinkedIn URLs already exist | count=%s",
            len(existing_urls),
        )

        return SourceInsertResult(
            inserted=[],
            existing_urls=sorted(existing_urls),
        )

    payloads = [
        {
            URL_COLUMN: url,
        }
        for url in new_urls
    ]

    response = (
        client
        .table(TABLE_NAME)
        .insert(payloads)
        .execute()
    )

    inserted_rows = list(response.data or [])

    logger.info(
        (
            "LinkedIn sources inserted | "
            "inserted=%s | existing=%s"
        ),
        len(inserted_rows),
        len(existing_urls),
    )

    return SourceInsertResult(
        inserted=inserted_rows,
        existing_urls=sorted(existing_urls),
    )
