from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urlsplit

from supabase import Client, create_client


logger = logging.getLogger("supabase-sources")


SUPABASE_URL = os.getenv(
    "SUPABASE_URL",
    "",
).strip()

SUPABASE_SECRET_KEY = os.getenv(
    "SUPABASE_SECRET_KEY",
    "",
).strip()


TABLE_NAME = "linkedin_sources"
URL_COLUMN = "linkedin_url"

HARD_MAX_URLS_PER_INSERT = 10

SUPPORTED_SOURCE_TYPES = {
    "profile",
    "company",
}


@dataclass(frozen=True)
class SourceInsertResult:
    """
    Kết quả insert LinkedIn sources.

    inserted:
        Những row vừa được Supabase tạo.

    existing_urls:
        Những URL đã tồn tại trước đó và không bị ghi đè.
    """

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


def clean_input_urls(
    urls: list[str],
) -> list[str]:
    """
    Chuẩn hóa danh sách URL đầu vào ở lớp storage.

    Parser phía trước đã normalize URL, nhưng lớp database
    vẫn tự bảo vệ để tránh dữ liệu lỗi khi hàm này được gọi
    từ một nơi khác.

    Logic:
    - Bỏ item rỗng.
    - Bỏ URL trùng nhau.
    - Giữ nguyên thứ tự xuất hiện.
    - Chặn cứng tối đa 10 URL.
    """
    if not isinstance(urls, list):
        raise TypeError(
            "urls must be a list"
        )

    cleaned_urls: list[str] = []
    seen: set[str] = set()

    for raw_url in urls:
        cleaned_url = str(
            raw_url or ""
        ).strip()

        if not cleaned_url:
            continue

        deduplication_key = (
            cleaned_url.casefold()
        )

        if deduplication_key in seen:
            continue

        seen.add(
            deduplication_key
        )

        cleaned_urls.append(
            cleaned_url
        )

    if (
        len(cleaned_urls)
        > HARD_MAX_URLS_PER_INSERT
    ):
        raise ValueError(
            "Cannot insert more than "
            f"{HARD_MAX_URLS_PER_INSERT} "
            "LinkedIn URLs in one request. "
            f"Received {len(cleaned_urls)}."
        )

    return cleaned_urls


def get_source_metadata_from_url(
    linkedin_url: str,
) -> dict[str, Any]:
    """
    Tạo dữ liệu tối thiểu bắt buộc từ LinkedIn URL.

    Profile:
        https://www.linkedin.com/in/test-user/

        {
            "name": "test-user",
            "source_type": "profile",
            "enabled": True
        }

    Company:
        https://www.linkedin.com/company/test-company/

        {
            "name": "test-company",
            "source_type": "company",
            "enabled": False
        }

    Company hiện được lưu nhưng chưa bật scan vì scraper hiện
    tại chỉ được thiết kế cho profile URL. Việc này tránh một
    company URL làm Mac scanner lỗi lặp lại ở mỗi batch.
    """
    if not isinstance(
        linkedin_url,
        str,
    ):
        raise TypeError(
            "linkedin_url must be a string"
        )

    cleaned_url = linkedin_url.strip()

    if not cleaned_url:
        raise ValueError(
            "LinkedIn URL cannot be empty"
        )

    try:
        parsed_url = urlsplit(
            cleaned_url
        )
    except ValueError as exc:
        raise ValueError(
            f"Invalid LinkedIn URL: {linkedin_url}"
        ) from exc

    hostname = (
        parsed_url.hostname or ""
    ).lower()

    valid_hostname = (
        hostname == "linkedin.com"
        or hostname.endswith(
            ".linkedin.com"
        )
    )

    if not valid_hostname:
        raise ValueError(
            "Unsupported LinkedIn hostname: "
            f"{hostname or '<empty>'}"
        )

    path_parts = [
        unquote(part).strip()
        for part in parsed_url.path.split("/")
        if part.strip()
    ]

    if len(path_parts) < 2:
        raise ValueError(
            f"Invalid LinkedIn URL: {linkedin_url}"
        )

    linkedin_path_type = (
        path_parts[0].lower()
    )

    slug = path_parts[1].strip()

    if not slug:
        raise ValueError(
            "LinkedIn URL has no slug: "
            f"{linkedin_url}"
        )

    if slug.casefold() in {
        "undefined",
        "null",
        "none",
    }:
        raise ValueError(
            "LinkedIn URL contains an invalid slug: "
            f"{linkedin_url}"
        )

    if linkedin_path_type == "in":
        source_type = "profile"
        enabled = True

    elif linkedin_path_type == "company":
        source_type = "company"

        # Company scanner chưa được triển khai.
        # Lưu source nhưng chưa đưa vào profile scan queue.
        enabled = False

    else:
        raise ValueError(
            "Unsupported LinkedIn URL type: "
            f"{linkedin_url}"
        )

    if source_type not in SUPPORTED_SOURCE_TYPES:
        raise ValueError(
            "Unsupported source type: "
            f"{source_type}"
        )

    return {
        "name": slug,
        "source_type": source_type,
        "enabled": enabled,
    }


def build_source_payloads(
    urls: list[str],
) -> list[dict[str, Any]]:
    """
    Validate toàn bộ URL và tạo payload trước khi thực hiện
    bất kỳ database mutation nào.

    Nếu một URL không hợp lệ, hàm raise ngay và Supabase chưa
    nhận lệnh insert nào.
    """
    payloads: list[dict[str, Any]] = []

    for url in urls:
        metadata = get_source_metadata_from_url(
            url
        )

        payloads.append(
            {
                "linkedin_url": url,
                "name": metadata["name"],
                "source_type": (
                    metadata["source_type"]
                ),
                "enabled": metadata["enabled"],
                "last_scanned_at": None,
            }
        )

    return payloads


def find_existing_urls(
    client: Client,
    urls: list[str],
) -> set[str]:
    """
    Kiểm tra URL nào đã tồn tại trong linkedin_sources.

    Sử dụng một query IN thay vì gọi một query cho mỗi URL.
    """
    if not urls:
        return set()

    response = (
        client
        .table(TABLE_NAME)
        .select(URL_COLUMN)
        .in_(
            URL_COLUMN,
            urls,
        )
        .execute()
    )

    existing_urls: set[str] = set()

    for row in list(
        response.data or []
    ):
        existing_url = str(
            row.get(URL_COLUMN) or ""
        ).strip()

        if existing_url:
            existing_urls.add(
                existing_url
            )

    return existing_urls


def order_existing_urls(
    *,
    input_urls: list[str],
    existing_urls: set[str],
) -> list[str]:
    """
    Trả existing URLs theo đúng thứ tự request ban đầu.
    """
    return [
        url
        for url in input_urls
        if url in existing_urls
    ]


def insert_new_linkedin_urls(
    urls: list[str],
) -> SourceInsertResult:
    """
    Insert các LinkedIn URL chưa tồn tại.

    Flow:
    1. Clean và deduplicate.
    2. Chặn tối đa 10 URL.
    3. Validate toàn bộ URL.
    4. Query URL đã tồn tại.
    5. Bulk insert URL mới trong một request.
    6. Không update hoặc ghi đè row cũ.

    Interface được giữ nguyên để tương thích với
    backend/main.py.
    """
    cleaned_urls = clean_input_urls(
        urls
    )

    if not cleaned_urls:
        return SourceInsertResult(
            inserted=[],
            existing_urls=[],
        )

    # Validate toàn bộ request trước khi tạo DB client
    # hoặc thực hiện mutation.
    all_payloads = build_source_payloads(
        cleaned_urls
    )

    payload_by_url = {
        str(payload["linkedin_url"]): payload
        for payload in all_payloads
    }

    client = get_supabase_client()

    existing_url_set = find_existing_urls(
        client=client,
        urls=cleaned_urls,
    )

    existing_urls = order_existing_urls(
        input_urls=cleaned_urls,
        existing_urls=existing_url_set,
    )

    new_urls = [
        url
        for url in cleaned_urls
        if url not in existing_url_set
    ]

    if not new_urls:
        logger.info(
            (
                "All LinkedIn URLs already exist | "
                "count=%s"
            ),
            len(existing_urls),
        )

        return SourceInsertResult(
            inserted=[],
            existing_urls=existing_urls,
        )

    new_payloads = [
        payload_by_url[url]
        for url in new_urls
    ]

    logger.info(
        (
            "Inserting LinkedIn sources | "
            "received=%s | "
            "new=%s | "
            "existing=%s | "
            "profile_sources=%s | "
            "company_sources=%s"
        ),
        len(cleaned_urls),
        len(new_payloads),
        len(existing_urls),
        sum(
            1
            for payload in new_payloads
            if payload["source_type"] == "profile"
        ),
        sum(
            1
            for payload in new_payloads
            if payload["source_type"] == "company"
        ),
    )

    # Một bulk insert request thay vì insert từng row.
    response = (
        client
        .table(TABLE_NAME)
        .insert(
            new_payloads
        )
        .execute()
    )

    inserted_rows = list(
        response.data or []
    )

    if len(inserted_rows) != len(new_payloads):
        raise RuntimeError(
            "Supabase returned an unexpected number "
            "of inserted rows. "
            f"Expected {len(new_payloads)}, "
            f"received {len(inserted_rows)}."
        )

    logger.info(
        (
            "LinkedIn sources inserted | "
            "inserted=%s | "
            "existing=%s"
        ),
        len(inserted_rows),
        len(existing_urls),
    )

    return SourceInsertResult(
        inserted=inserted_rows,
        existing_urls=existing_urls,
    )
