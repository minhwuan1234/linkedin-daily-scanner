from __future__ import annotations

import os
import re
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit


DEFAULT_MAX_URLS_PER_REQUEST = 10
HARD_MAX_URLS_PER_REQUEST = 10


LINKEDIN_URL_PATTERN = re.compile(
    r"https?://(?:[\w-]+\.)?linkedin\.com/"
    r"(?:in|company)/[^\s<>\[\]\"']+",
    re.IGNORECASE,
)


class LinkedInUrlParserError(ValueError):
    """
    Base error cho LinkedIn URL parser.
    """


class LinkedInUrlLimitError(
    LinkedInUrlParserError
):
    """
    Request chứa nhiều LinkedIn URL hợp lệ hơn giới hạn.
    """

    def __init__(
        self,
        *,
        found_count: int,
        max_count: int,
    ) -> None:
        self.found_count = int(found_count)
        self.max_count = int(max_count)

        super().__init__(
            "Too many LinkedIn URLs in one request. "
            f"Found {self.found_count}; "
            f"maximum is {self.max_count}."
        )


@dataclass(frozen=True)
class LinkedInUrlParseResult:
    """
    Kết quả parse LinkedIn URL đã chuẩn hóa.

    urls:
        Danh sách URL hợp lệ, không trùng nhau.

    matched_count:
        Số chuỗi URL LinkedIn được regex tìm thấy trước
        khi normalize và loại trùng.

    valid_count:
        Số URL hợp lệ sau khi normalize và loại trùng.
    """

    urls: list[str]
    matched_count: int
    valid_count: int


def _read_positive_int_env(
    key: str,
    *,
    default: int,
) -> int:
    """
    Đọc positive integer từ environment variable.
    """
    raw_value = os.getenv(key)

    if raw_value is None:
        return default

    try:
        value = int(raw_value.strip())
    except ValueError as exc:
        raise ValueError(
            f"Invalid integer environment variable "
            f"{key}={raw_value!r}"
        ) from exc

    if value < 1:
        raise ValueError(
            f"{key} must be at least 1. "
            f"Received {value}."
        )

    return value


def get_max_urls_per_request() -> int:
    """
    Lấy gateway limit từ environment.

    Hệ thống có hard cap là 10. Không cho cấu hình lớn hơn
    10 để tránh Railway nhận request quá lớn ngoài dự kiến.
    """
    configured_limit = _read_positive_int_env(
        "LINKEDIN_MAX_URLS_PER_REQUEST",
        default=DEFAULT_MAX_URLS_PER_REQUEST,
    )

    if configured_limit > HARD_MAX_URLS_PER_REQUEST:
        raise ValueError(
            "LINKEDIN_MAX_URLS_PER_REQUEST cannot "
            f"exceed {HARD_MAX_URLS_PER_REQUEST}. "
            f"Received {configured_limit}."
        )

    return configured_limit


def normalize_linkedin_url(
    raw_url: str,
) -> str | None:
    """
    Chuẩn hóa LinkedIn profile hoặc company URL.

    Ví dụ:
        https://linkedin.com/in/example?trk=abc

    Thành:
        https://www.linkedin.com/in/example/

    Chỉ giữ:
        /in/<slug>/
        /company/<slug>/

    Query, fragment và path phụ đều bị loại bỏ.
    """
    if not isinstance(raw_url, str):
        return None

    cleaned_url = raw_url.strip().rstrip(
        ".,;:!?)]}>\"'"
    )

    if not cleaned_url:
        return None

    try:
        parsed_url = urlsplit(
            cleaned_url
        )
    except ValueError:
        return None

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
        return None

    path_parts = [
        part.strip()
        for part in parsed_url.path.split("/")
        if part.strip()
    ]

    if len(path_parts) < 2:
        return None

    linkedin_type = (
        path_parts[0].lower()
    )

    slug = path_parts[1].strip()

    if linkedin_type not in {
        "in",
        "company",
    }:
        return None

    if not slug:
        return None

    # Tránh một số path không phải source thực.
    if slug.casefold() in {
        "undefined",
        "null",
        "none",
    }:
        return None

    normalized_path = (
        f"/{linkedin_type}/{slug}/"
    )

    return urlunsplit(
        (
            "https",
            "www.linkedin.com",
            normalized_path,
            "",
            "",
        )
    )


def parse_linkedin_urls(
    text: str,
) -> LinkedInUrlParseResult:
    """
    Tách, normalize và loại URL trùng nhau.

    Hàm này chưa áp dụng gateway limit. Nó chỉ parse dữ liệu.

    Giữ nguyên thứ tự xuất hiện đầu tiên của từng URL.
    """
    safe_text = (
        text
        if isinstance(text, str)
        else ""
    )

    matches = LINKEDIN_URL_PATTERN.findall(
        safe_text
    )

    urls: list[str] = []
    seen: set[str] = set()

    for raw_url in matches:
        normalized_url = (
            normalize_linkedin_url(
                raw_url
            )
        )

        if not normalized_url:
            continue

        deduplication_key = (
            normalized_url.casefold()
        )

        if deduplication_key in seen:
            continue

        seen.add(
            deduplication_key
        )

        urls.append(
            normalized_url
        )

    return LinkedInUrlParseResult(
        urls=urls,
        matched_count=len(matches),
        valid_count=len(urls),
    )


def extract_linkedin_urls(
    text: str,
) -> list[str]:
    """
    API tương thích với code cũ.

    Tách, chuẩn hóa và loại LinkedIn URL trùng nhau.

    Hàm này chưa raise limit error để tránh làm gãy
    backend/main.py trước khi file đó được update.

    Gateway thật sẽ gọi:
        extract_linkedin_urls_with_limit()
    """
    result = parse_linkedin_urls(
        text
    )

    return result.urls


def extract_linkedin_urls_with_limit(
    text: str,
    *,
    max_urls: int | None = None,
) -> list[str]:
    """
    Parse LinkedIn URLs và áp dụng gateway limit.

    Nếu số URL hợp lệ, unique vượt giới hạn:
    - raise LinkedInUrlLimitError
    - không trả 10 URL đầu
    - không cho downstream insert một phần request

    max_urls:
        Có thể truyền trực tiếp khi test.

        Nếu không truyền, đọc từ:
            LINKEDIN_MAX_URLS_PER_REQUEST
    """
    resolved_max_urls = (
        get_max_urls_per_request()
        if max_urls is None
        else int(max_urls)
    )

    if resolved_max_urls < 1:
        raise ValueError(
            "max_urls must be at least 1."
        )

    if (
        resolved_max_urls
        > HARD_MAX_URLS_PER_REQUEST
    ):
        raise ValueError(
            "max_urls cannot exceed "
            f"{HARD_MAX_URLS_PER_REQUEST}."
        )

    result = parse_linkedin_urls(
        text
    )

    if result.valid_count > resolved_max_urls:
        raise LinkedInUrlLimitError(
            found_count=result.valid_count,
            max_count=resolved_max_urls,
        )

    return result.urls


def detect_linkedin_source_type(
    url: str,
) -> str | None:
    """
    Xác định URL là profile hay company.
    """
    try:
        path = urlsplit(url).path.lower()
    except (
        TypeError,
        ValueError,
    ):
        return None

    if path.startswith("/in/"):
        return "profile"

    if path.startswith("/company/"):
        return "company"

    return None
