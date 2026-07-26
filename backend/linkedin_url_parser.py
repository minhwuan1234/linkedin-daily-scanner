import re
from urllib.parse import urlsplit, urlunsplit


LINKEDIN_URL_PATTERN = re.compile(
    r"https?://(?:[\w-]+\.)?linkedin\.com/"
    r"(?:in|company)/[^\s<>\[\]\"']+",
    re.IGNORECASE,
)


def normalize_linkedin_url(raw_url: str) -> str | None:
    """
    Chuẩn hóa LinkedIn profile hoặc company URL.

    Ví dụ:
    https://linkedin.com/in/example?trk=abc

    Thành:
    https://www.linkedin.com/in/example/
    """
    cleaned_url = raw_url.strip().rstrip(
        ".,;:!?)]}>\"'"
    )

    try:
        parsed_url = urlsplit(cleaned_url)
    except ValueError:
        return None

    hostname = (parsed_url.hostname or "").lower()

    valid_hostname = (
        hostname == "linkedin.com"
        or hostname.endswith(".linkedin.com")
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

    linkedin_type = path_parts[0].lower()
    slug = path_parts[1]

    if linkedin_type not in {"in", "company"}:
        return None

    if not slug:
        return None

    normalized_path = f"/{linkedin_type}/{slug}/"

    return urlunsplit(
        (
            "https",
            "www.linkedin.com",
            normalized_path,
            "",
            "",
        )
    )


def extract_linkedin_urls(text: str) -> list[str]:
    """
    Tách, chuẩn hóa và loại bỏ LinkedIn URL trùng nhau.
    Giữ nguyên thứ tự URL xuất hiện trong tin nhắn.
    """
    matches = LINKEDIN_URL_PATTERN.findall(text or "")

    urls: list[str] = []
    seen: set[str] = set()

    for raw_url in matches:
        normalized_url = normalize_linkedin_url(raw_url)

        if not normalized_url:
            continue

        if normalized_url in seen:
            continue

        seen.add(normalized_url)
        urls.append(normalized_url)

    return urls


def detect_linkedin_source_type(url: str) -> str | None:
    """
    Xác định URL là profile hay company.
    """
    path = urlsplit(url).path.lower()

    if path.startswith("/in/"):
        return "profile"

    if path.startswith("/company/"):
        return "company"

    return None
