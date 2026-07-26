import logging
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urlsplit

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
    Tạo Supabase client dành cho Railway backend.
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


def get_source_metadata_from_url(
    linkedin_url: str,
) -> dict[str, str]:
    """
    Tạo dữ liệu tối thiểu bắt buộc từ LinkedIn URL.

    Ví dụ:
    https://www.linkedin.com/in/test-user/
    ->
    {
        "name": "test-user",
        "source_type": "profile"
    }

    Giá trị name chỉ là placeholder kỹ thuật.
    Scraper sẽ update name thật sau.
    """
    parsed_url = urlsplit(linkedin_url)

    path_parts = [
        unquote(part).strip()
        for part in parsed_url.path.split("/")
        if part.strip()
    ]

    if len(path_parts) < 2:
        raise ValueError(
            f"Invalid LinkedIn URL: {linkedin_url}"
        )

    linkedin_path_type = path_parts[0].lower()
    slug = path_parts[1].strip()

    if not slug:
        raise ValueError(
            f"LinkedIn URL has no slug: {linkedin_url}"
        )

    if linkedin_path_type == "in":
        source_type = "profile"
    elif linkedin_path_type == "company":
        source_type = "company"
    else:
        raise ValueError(
            f"Unsupported LinkedIn URL type: {linkedin_url}"
        )

    return {
        "name": slug,
        "source_type": source_type,
    }


def find_existing_urls(
    client: Client,
    urls: list[str],
) -> set[str]:
    """
    Kiểm tra URL nào đã tồn tại trong linkedin_sources.
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
    Insert các LinkedIn URL chưa tồn tại.

    Vì bảng linkedin_sources bắt buộc cột name,
    payload sẽ gồm:

    - linkedin_url
    - name: tạm lấy từ slug URL
    - source_type: profile hoặc company

    Không update hoặc ghi đè các row đã tồn tại.
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

    payloads: list[dict[str, Any]] = []

    for url in new_urls:
        metadata = get_source_metadata_from_url(url)

        payloads.append(
            {
                "linkedin_url": url,
                "name": metadata["name"],
                "source_type": metadata["source_type"],
            }
        )

    logger.info(
        "Preparing LinkedIn source payloads: %s",
        payloads,
    )

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
