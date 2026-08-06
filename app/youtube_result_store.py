from dotenv import load_dotenv

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Iterable

from supabase import Client, create_client


load_dotenv()

YOUTUBE_CHANNEL_TABLE = "youtube_scan_channels"


class YouTubeResultStoreError(RuntimeError):
    """
    Lỗi khi chuẩn hóa hoặc lưu kết quả scan YouTube.
    """


def get_supabase_client() -> Client:
    """
    Tạo Supabase client từ biến môi trường.

    Ưu tiên service-role key để worker có quyền ghi dữ liệu.
    """

    supabase_url = os.getenv(
        "SUPABASE_URL",
        "",
    ).strip()

    supabase_key = (
        os.getenv(
            "SUPABASE_SERVICE_ROLE_KEY",
            "",
        ).strip()
        or os.getenv(
            "SUPABASE_KEY",
            "",
        ).strip()
        or os.getenv(
            "SUPABASE_ANON_KEY",
            "",
        ).strip()
    )

    if not supabase_url:
        raise YouTubeResultStoreError(
            "Missing SUPABASE_URL environment variable."
        )

    if not supabase_key:
        raise YouTubeResultStoreError(
            "Missing SUPABASE_SERVICE_ROLE_KEY, "
            "SUPABASE_KEY, or SUPABASE_ANON_KEY."
        )

    return create_client(
        supabase_url,
        supabase_key,
    )


def _clean_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return str(
        value
    ).strip()


def _clean_integer(
    value: Any,
) -> int | None:
    if value is None or value == "":
        return None

    if isinstance(
        value,
        bool,
    ):
        return None

    try:
        return int(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return None


def _clean_links(
    value: Any,
) -> list[dict[str, str]]:
    """
    Chỉ giữ các link hợp lệ dưới dạng:
    {"title": "...", "url": "..."}
    """

    if not isinstance(
        value,
        list,
    ):
        return []

    links: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for item in value:
        if not isinstance(
            item,
            dict,
        ):
            continue

        title = _clean_text(
            item.get(
                "title",
                "",
            )
        )
        url = _clean_text(
            item.get(
                "url",
                "",
            )
        )

        if not url or url in seen_urls:
            continue

        seen_urls.add(
            url
        )

        links.append(
            {
                "title": title,
                "url": url,
            }
        )

    return links


def build_channel_row(
    *,
    job_id: str,
    channel: dict[str, Any],
) -> dict[str, Any]:
    """
    Chuyển output của youtube_scanner thành row để lưu Supabase.
    """

    cleaned_job_id = _clean_text(
        job_id
    )
    channel_url = _clean_text(
        channel.get(
            "channel_url",
            "",
        )
    )

    if not cleaned_job_id:
        raise YouTubeResultStoreError(
            "job_id is required."
        )

    if not channel_url:
        raise YouTubeResultStoreError(
            "channel_url is required."
        )

    email = _clean_text(
        channel.get(
            "email",
            "",
        )
    )
    email_status = _clean_text(
        channel.get(
            "email_status",
            "",
        )
    )

    if not email_status:
        email_status = (
            "available"
            if email
            else "unavailable"
        )

    return {
        "job_id": cleaned_job_id,
        "channel_url": channel_url,
        "channel_name": _clean_text(
            channel.get(
                "channel_name",
                "",
            )
        ),
        "subscriber_count_text": _clean_text(
            channel.get(
                "subscriber_count_text",
                "",
            )
        ),
        "subscriber_count": _clean_integer(
            channel.get(
                "subscriber_count",
            )
        ),
        "video_count_text": _clean_text(
            channel.get(
                "video_count_text",
                "",
            )
        ),
        "video_count": _clean_integer(
            channel.get(
                "video_count",
            )
        ),
        "channel_description": _clean_text(
            channel.get(
                "channel_description",
                "",
            )
        ),
        "location": _clean_text(
            channel.get(
                "location",
                "",
            )
        ),
        "email": email,
        "email_status": email_status,
        "total_views_text": _clean_text(
            channel.get(
                "total_views_text",
                "",
            )
        ),
        "total_views": _clean_integer(
            channel.get(
                "total_views",
            )
        ),
        "channel_links": _clean_links(
            channel.get(
                "channel_links",
                [],
            )
        ),
        "scan_status": _clean_text(
            channel.get(
                "scan_status",
                "completed",
            )
        )
        or "completed",
        "scanned_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }


def save_channel_result(
    *,
    job_id: str,
    channel: dict[str, Any],
    client: Client | None = None,
) -> dict[str, Any]:
    """
    Upsert một channel.

    Cần unique index:
    (job_id, channel_url)
    """

    active_client = (
        client
        if client is not None
        else get_supabase_client()
    )

    row = build_channel_row(
        job_id=job_id,
        channel=channel,
    )

    try:
        response = (
            active_client.table(
                YOUTUBE_CHANNEL_TABLE
            )
            .upsert(
                row,
                on_conflict=(
                    "job_id,channel_url"
                ),
            )
            .execute()
        )
    except Exception as error:
        raise YouTubeResultStoreError(
            "Could not save YouTube channel "
            f"{row['channel_url']}: {error}"
        ) from error

    data = getattr(
        response,
        "data",
        None,
    )

    if isinstance(
        data,
        list,
    ) and data:
        return data[0]

    return row


def save_channel_results(
    *,
    job_id: str,
    channels: Iterable[dict[str, Any]],
    client: Client | None = None,
) -> list[dict[str, Any]]:
    """
    Upsert nhiều channel trong một request.
    """

    active_client = (
        client
        if client is not None
        else get_supabase_client()
    )

    rows = [
        build_channel_row(
            job_id=job_id,
            channel=channel,
        )
        for channel in channels
    ]

    if not rows:
        return []

    try:
        response = (
            active_client.table(
                YOUTUBE_CHANNEL_TABLE
            )
            .upsert(
                rows,
                on_conflict=(
                    "job_id,channel_url"
                ),
            )
            .execute()
        )
    except Exception as error:
        raise YouTubeResultStoreError(
            "Could not save YouTube channel results: "
            f"{error}"
        ) from error

    data = getattr(
        response,
        "data",
        None,
    )

    if isinstance(
        data,
        list,
    ):
        return data

    return rows
