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


@dataclass(frozen=True)
class SourceInsertResult:
    """
    Kết quả xử lý LinkedIn sources.

    inserted:
        Những row mới được tạo.

    existing_urls:
        Những URL đã tồn tại và được đưa lại vào queue scan.
    """

    inserted: list[dict[str, Any]]
    existing_urls: list[str]

    @property
    def inserted_count(self) -> int:
        return len(self.inserted)

    @property
    def existing_count(self) -> int:
        return len(self.existing_urls)


def _as_optional_text(
    value: Any,
) -> str | None:
    """
    Chuẩn hóa metadata thành text hoặc None.
    """
    if value is None:
        return None

    text = str(value).strip()

    return text or None


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
    Clean, deduplicate và giới hạn URL đầu vào.
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
            "Cannot process more than "
            f"{HARD_MAX_URLS_PER_INSERT} "
            "LinkedIn URLs in one request. "
            f"Received {len(cleaned_urls)}."
        )

    return cleaned_urls


def get_source_metadata_from_url(
    linkedin_url: str,
) -> dict[str, Any]:
    """
    Tạo metadata kỹ thuật ban đầu từ LinkedIn URL.

    Profile được bật scan.

    Company được lưu nhưng chưa bật scan vì scraper hiện tại
    chỉ hỗ trợ cấu trúc profile /in/.
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
        enabled = False

    else:
        raise ValueError(
            "Unsupported LinkedIn URL type: "
            f"{linkedin_url}"
        )

    return {
        "name": slug,
        "source_type": source_type,
        "enabled": enabled,
    }


def build_lark_metadata(
    *,
    chat_id: str | None,
    message_id: str | None,
    sender_open_id: str | None,
) -> dict[str, Any]:
    """
    Tạo metadata dùng để gửi kết quả về Lark.

    Trạng thái gửi cũ luôn được reset khi có request mới.
    """
    return {
        "lark_chat_id": _as_optional_text(
            chat_id
        ),
        "lark_message_id": _as_optional_text(
            message_id
        ),
        "lark_sender_open_id": _as_optional_text(
            sender_open_id
        ),
        "lark_result_sent_at": None,
        "lark_result_error": None,
    }


def build_source_payloads(
    urls: list[str],
    *,
    chat_id: str | None = None,
    message_id: str | None = None,
    sender_open_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Validate toàn bộ URL và tạo payload trước khi insert.

    Không ghi database trong hàm này.
    """
    lark_metadata = build_lark_metadata(
        chat_id=chat_id,
        message_id=message_id,
        sender_open_id=sender_open_id,
    )

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
                **lark_metadata,
            }
        )

    return payloads


def find_existing_source_rows(
    client: Client,
    urls: list[str],
) -> list[dict[str, Any]]:
    """
    Lấy các source đã tồn tại trong một query.
    """
    if not urls:
        return []

    response = (
        client
        .table(TABLE_NAME)
        .select(
            "id,linkedin_url,source_type,enabled"
        )
        .in_(
            URL_COLUMN,
            urls,
        )
        .execute()
    )

    return list(
        response.data or []
    )


def update_existing_source_request(
    *,
    client: Client,
    source_row: dict[str, Any],
    chat_id: str | None,
    message_id: str | None,
    sender_open_id: str | None,
) -> dict[str, Any]:
    """
    Đưa một source đã tồn tại trở lại queue scan.

    Logic:
    - Update metadata Lark mới nhất.
    - Reset last_scanned_at.
    - Reset trạng thái gửi result.
    - Không thay đổi name hoặc source_type hiện có.
    """
    source_id_raw = source_row.get("id")

    if source_id_raw is None:
        raise RuntimeError(
            "Existing source row is missing id"
        )

    source_id = int(
        source_id_raw
    )

    source_type = str(
        source_row.get("source_type") or ""
    ).strip().lower()

    update_payload = {
        **build_lark_metadata(
            chat_id=chat_id,
            message_id=message_id,
            sender_open_id=sender_open_id,
        ),
        "last_scanned_at": None,
    }

    # Profile được đưa trở lại queue.
    # Company vẫn disabled cho đến khi có company scraper.
    if source_type == "profile":
        update_payload["enabled"] = True

    elif source_type == "company":
        update_payload["enabled"] = False

    response = (
        client
        .table(TABLE_NAME)
        .update(
            update_payload
        )
        .eq(
            "id",
            source_id,
        )
        .execute()
    )

    rows = list(
        response.data or []
    )

    if not rows:
        raise RuntimeError(
            "Supabase did not return the updated "
            f"source row for id={source_id}"
        )

    return rows[0]


def insert_new_linkedin_urls(
    urls: list[str],
    *,
    chat_id: str | None = None,
    message_id: str | None = None,
    sender_open_id: str | None = None,
) -> SourceInsertResult:
    """
    Insert URL mới và requeue URL đã tồn tại.

    Interface cũ vẫn hợp lệ:

        insert_new_linkedin_urls(urls)

    Interface mới:

        insert_new_linkedin_urls(
            urls,
            chat_id=chat_id,
            message_id=message_id,
            sender_open_id=open_id,
        )
    """
    cleaned_urls = clean_input_urls(
        urls
    )

    if not cleaned_urls:
        return SourceInsertResult(
            inserted=[],
            existing_urls=[],
        )

    all_payloads = build_source_payloads(
        cleaned_urls,
        chat_id=chat_id,
        message_id=message_id,
        sender_open_id=sender_open_id,
    )

    payload_by_url = {
        str(payload["linkedin_url"]): payload
        for payload in all_payloads
    }

    client = get_supabase_client()

    existing_rows = find_existing_source_rows(
        client=client,
        urls=cleaned_urls,
    )

    existing_row_by_url = {
        str(row.get("linkedin_url") or ""): row
        for row in existing_rows
        if row.get("linkedin_url")
    }

    existing_urls = [
        url
        for url in cleaned_urls
        if url in existing_row_by_url
    ]

    new_urls = [
        url
        for url in cleaned_urls
        if url not in existing_row_by_url
    ]

    # Requeue existing sources với metadata Lark mới nhất.
    for url in existing_urls:
        update_existing_source_request(
            client=client,
            source_row=existing_row_by_url[url],
            chat_id=chat_id,
            message_id=message_id,
            sender_open_id=sender_open_id,
        )

    new_payloads = [
        payload_by_url[url]
        for url in new_urls
    ]

    inserted_rows: list[dict[str, Any]] = []

    if new_payloads:
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

        if len(inserted_rows) != len(
            new_payloads
        ):
            raise RuntimeError(
                "Supabase returned an unexpected "
                "number of inserted rows. "
                f"Expected {len(new_payloads)}, "
                f"received {len(inserted_rows)}."
            )

    logger.info(
        (
            "LinkedIn source request processed | "
            "received=%s | inserted=%s | "
            "requeued=%s | chat_id_present=%s"
        ),
        len(cleaned_urls),
        len(inserted_rows),
        len(existing_urls),
        bool(
            _as_optional_text(chat_id)
        ),
    )

    return SourceInsertResult(
        inserted=inserted_rows,
        existing_urls=existing_urls,
    )
