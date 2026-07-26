import re
from urllib.parse import urlsplit, urlunsplit


LINKEDIN_URL_PATTERN = re.compile(
    r"https?://(?:[\w-]+\.)?linkedin\.com/"
    r"(?:in|company)/[^\s<>\[\]\"']+",
    re.IGNORECASE,
)


def normalize_linkedin_url(raw_url: str) -> str | None:
    """
    Chuẩn hóa LinkedIn profile/company URL.

    Ví dụ:
    https://linkedin.com/in/tony?trk=test
    ->
    https://www.linkedin.com/in/tony/
    """
    cleaned_url = raw_url.strip().rstrip(
        ".,;:!?)]}>\"'"
    )

    try:
        parts = urlsplit(cleaned_url)
    except ValueError:
        return None

    hostname = (parts.hostname or "").lower()

    if not (
        hostname == "linkedin.com"
        or hostname.endswith(".linkedin.com")
    ):
        return None

    path_parts = [
        part
        for part in parts.path.split("/")
        if part
    ]

    if len(path_parts) < 2:
        return None

    source_type = path_parts[0].lower()

    if source_type not in {"in", "company"}:
        return None

    slug = path_parts[1].strip()

    if not slug:
        return None

    normalized_path = f"/{source_type}/{slug}/"

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
    Tìm tất cả LinkedIn profile/company URL trong text,
    chuẩn hóa và loại URL trùng.
    """
    matches = LINKEDIN_URL_PATTERN.findall(text or "")

    results: list[str] = []
    seen: set[str] = set()

    for raw_url in matches:
        normalized_url = normalize_linkedin_url(raw_url)

        if not normalized_url:
            continue

        if normalized_url in seen:
            continue

        seen.add(normalized_url)
        results.append(normalized_url)

    return results


def detect_linkedin_source_type(url: str) -> str | None:
    """
    Trả về profile hoặc company.
    """
    path = urlsplit(url).path.lower()

    if path.startswith("/in/"):
        return "profile"

    if path.startswith("/company/"):
        return "company"

    return None
