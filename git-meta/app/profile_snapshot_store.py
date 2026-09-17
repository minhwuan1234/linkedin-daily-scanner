from __future__ import annotations

import json
from typing import Any

from app.linkedin_scanner import create_supabase_client
from app.settings import Settings


SNAPSHOT_TABLE = "linkedin_profile_snapshots"
SOURCE_TABLE = "linkedin_sources"
POST_CAPTION_LIMIT = 5


def _as_text(value: Any) -> str | None:
    """
    Chuẩn hóa giá trị thành text để ghi Supabase.

    Trả None nếu giá trị rỗng.
    """
    if value is None:
        return None

    text = str(value).strip()

    return text or None


def _as_dict(value: Any) -> dict[str, Any]:
    """
    Đảm bảo giá trị luôn là dictionary hợp lệ.
    """
    if isinstance(value, dict):
        return value

    return {}


def _as_list(value: Any) -> list[Any]:
    """
    Đảm bảo giá trị luôn là list hợp lệ.
    """
    if isinstance(value, list):
        return value

    return []


def _normalize_post_captions(
    value: Any,
) -> list[str]:
    """
    Chuẩn hóa danh sách caption.

    Chỉ giữ:
    - caption dạng string hợp lệ
    - tối đa 5 caption
    - không giữ caption rỗng
    - không giữ caption trùng nhau

    Không dùng AI để suy luận hoặc tạo caption.
    """
    raw_items = _as_list(value)

    captions: list[str] = []
    seen: set[str] = set()

    for item in raw_items:
        caption: str | None = None

        if isinstance(item, str):
            caption = _as_text(item)

        elif isinstance(item, dict):
            for key in (
                "caption",
                "text",
                "content",
                "post_text",
                "description",
            ):
                caption = _as_text(
                    item.get(key)
                )

                if caption:
                    break

        if not caption:
            continue

        normalized = caption.casefold()

        if normalized in seen:
            continue

        seen.add(normalized)
        captions.append(caption)

        if len(captions) >= POST_CAPTION_LIMIT:
            break

    return captions


def _get_post_caption(
    captions: list[str],
    index: int,
) -> str | None:
    """
    Lấy caption theo vị trí.

    Trả None nếu không có caption tương ứng.
    """
    if index < 0:
        return None

    if index >= len(captions):
        return None

    return _as_text(captions[index])


def _extract_recent_post_captions(
    *,
    result: dict[str, Any],
    profile: dict[str, Any],
    raw_profile_data: dict[str, Any],
) -> list[str]:
    """
    Lấy recent post captions theo thứ tự ưu tiên.

    Output mới của profile_raw_scraper:
        result["recent_post_captions"]

    Các fallback được giữ lại để tương thích dữ liệu cũ.
    """
    candidates = (
        result.get("recent_post_captions"),
        result.get("posts"),
        profile.get("recent_post_captions"),
        profile.get("recent_posts"),
        raw_profile_data.get(
            "recent_post_captions"
        ),
        raw_profile_data.get("posts"),
    )

    for candidate in candidates:
        captions = _normalize_post_captions(
            candidate
        )

        if captions:
            return captions

    return []


def build_snapshot_payload(
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    Chuyển kết quả scraper sang đúng schema của bảng
    public.linkedin_profile_snapshots.

    Một source_id chỉ có một snapshot row.
    Những lần scan sau sẽ update row hiện tại.
    """
    source_id_raw = result.get("source_id")

    if source_id_raw is None:
        raise ValueError(
            "Scrape result is missing source_id"
        )

    source_id = int(source_id_raw)

    scraped_at = _as_text(
        result.get("scraped_at")
    )

    if not scraped_at:
        raise ValueError(
            "Scrape result is missing scraped_at"
        )

    profile = _as_dict(
        result.get("profile")
    )

    raw_profile_data = _as_dict(
        result.get("raw_profile_data")
    )

    if not raw_profile_data:
        raw_profile_data = _as_dict(
            result.get("profile_data")
        )

    recent_post_captions = (
        _extract_recent_post_captions(
            result=result,
            profile=profile,
            raw_profile_data=(
                raw_profile_data
            ),
        )
    )

    errors = _as_list(
        result.get("errors")
    )

    experience_raw_text = _as_text(
        result.get("experience_raw_text")
    )

    if not experience_raw_text:
        experience_raw_text = _as_text(
            raw_profile_data.get(
                "experience_raw_text"
            )
        )

    linkedin_url = (
        _as_text(
            profile.get("linkedin_url")
        )
        or _as_text(
            result.get("linkedin_url")
        )
        or _as_text(
            raw_profile_data.get(
                "linkedin_url"
            )
        )
    )

    followers_count_text = (
        _as_text(
            profile.get(
                "followers_count_text"
            )
        )
        or _as_text(
            profile.get("followers")
        )
        or _as_text(
            raw_profile_data.get(
                "followers_count_text"
            )
        )
    )

    connections_count_text = (
        _as_text(
            profile.get(
                "connections_count_text"
            )
        )
        or _as_text(
            profile.get("connections")
        )
        or _as_text(
            raw_profile_data.get(
                "connections_count_text"
            )
        )
    )

    profile_data: dict[str, Any] = {
        "profile": profile,
        "experience_raw_text": (
            experience_raw_text
        ),
        "recent_post_captions": (
            recent_post_captions
        ),
    }

    normalized_raw_profile_data = {
        **raw_profile_data,
        "profile": (
            raw_profile_data.get("profile")
            or profile
        ),
        "experience_raw_text": (
            raw_profile_data.get(
                "experience_raw_text"
            )
            or experience_raw_text
        ),
        "recent_post_captions": (
            raw_profile_data.get(
                "recent_post_captions"
            )
            or recent_post_captions
        ),
    }

    payload: dict[str, Any] = {
        "source_id": source_id,
        "scraped_at": scraped_at,
        "profile_data": profile_data,
        "experience_raw_text": (
            experience_raw_text
        ),
        "errors": errors,
        "name": (
            _as_text(
                profile.get("name")
            )
            or _as_text(
                result.get("name")
            )
        ),
        "linkedin_url": linkedin_url,
        "headline": (
            _as_text(
                profile.get("headline")
            )
            or _as_text(
                result.get("headline")
            )
        ),
        "location": (
            _as_text(
                profile.get("location")
            )
            or _as_text(
                result.get("location")
            )
        ),
        "followers_count_text": (
            followers_count_text
        ),
        "connections_count_text": (
            connections_count_text
        ),
        "about_text": (
            _as_text(
                profile.get("about_text")
            )
            or _as_text(
                profile.get("about")
            )
            or _as_text(
                result.get("about_text")
            )
        ),
        "raw_profile_data": (
            normalized_raw_profile_data
        ),
        "post_1_caption": (
            _get_post_caption(
                recent_post_captions,
                0,
            )
        ),
        "post_2_caption": (
            _get_post_caption(
                recent_post_captions,
                1,
            )
        ),
        "post_3_caption": (
            _get_post_caption(
                recent_post_captions,
                2,
            )
        ),
        "post_4_caption": (
            _get_post_caption(
                recent_post_captions,
                3,
            )
        ),
        "post_5_caption": (
            _get_post_caption(
                recent_post_captions,
                4,
            )
        ),
    }

    return payload


def save_profile_snapshot(
    *,
    settings: Settings,
    result: dict[str, Any],
) -> int:
    """
    Upsert dữ liệu scan vào linkedin_profile_snapshots.

    Constraint của database:
        unique(source_id)

    Vì vậy:
    - source chưa từng scan: tạo row mới
    - source đã scan: update row cũ
    """
    client = create_supabase_client(
        settings
    )

    payload = build_snapshot_payload(
        result
    )

    response = (
        client
        .table(SNAPSHOT_TABLE)
        .upsert(
            payload,
            on_conflict="source_id",
        )
        .execute()
    )

    rows = list(
        response.data or []
    )

    if not rows:
        raise RuntimeError(
            "Supabase did not return a snapshot row"
        )

    snapshot_id = rows[0].get("id")

    if snapshot_id is None:
        raise RuntimeError(
            "Snapshot row does not contain id"
        )

    return int(snapshot_id)


def mark_source_scanned(
    *,
    settings: Settings,
    source_id: int,
    scanned_at: str,
) -> None:
    """
    Đánh dấu source đã scan xong trong linkedin_sources.

    Không ghi dữ liệu profile vào linkedin_sources.
    Bảng này chỉ giữ URL đầu vào và trạng thái scan.
    """
    client = create_supabase_client(
        settings
    )

    response = (
        client
        .table(SOURCE_TABLE)
        .update(
            {
                "last_scanned_at": (
                    scanned_at
                ),
            }
        )
        .eq(
            "id",
            int(source_id),
        )
        .execute()
    )

    if response.data is None:
        raise RuntimeError(
            f"Could not mark source "
            f"{source_id} as scanned"
        )


def debug_snapshot_payload(
    result: dict[str, Any],
) -> str:
    """
    Xem payload trước khi ghi Supabase.

    Không gọi trong production nếu raw data
    chứa thông tin nhạy cảm.
    """
    payload = build_snapshot_payload(
        result
    )

    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        default=str,
    )
