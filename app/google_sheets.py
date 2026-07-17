from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlparse

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from app.settings import Settings


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


@dataclass(frozen=True)
class LinkedInSource:
    name: str
    email_1: str
    email_2: str
    role: str
    company: str
    linkedin_url: str
    description: str
    coaching_available: str
    coaching_method: str
    coaching_language: str
    coaching: str
    location: str


def create_sheets_service(settings: Settings):
    service_account_info = json.loads(
        settings.google_service_account_json
    )

    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES,
    )

    return build(
        "sheets",
        "v4",
        credentials=credentials,
        cache_discovery=False,
    )


def normalize_linkedin_url(url: str) -> str:
    """
    Chuẩn hóa URL LinkedIn để hạn chế trùng lặp.

    Ví dụ:
    http://linkedin.com/in/example
    https://www.linkedin.com/in/example/
    đều được đưa về cùng một dạng.
    """
    value = url.strip()

    if not value:
        return ""

    if not value.startswith(("http://", "https://")):
        value = "https://" + value

    parsed = urlparse(value)

    hostname = parsed.netloc.lower().replace("linkedin.com", "www.linkedin.com")
    path = parsed.path.rstrip("/")

    if hostname != "www.linkedin.com":
        return ""

    if not (
        path.startswith("/in/")
        or path.startswith("/company/")
    ):
        return ""

    return f"https://www.linkedin.com{path}/"


def load_linkedin_sources(
    settings: Settings,
    sheet_range: str = "Trang tính1!A2:L",
) -> list[LinkedInSource]:
    service = create_sheets_service(settings)

    response = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=settings.google_sheet_id,
            range=sheet_range,
        )
        .execute()
    )

    rows = response.get("values", [])

    sources: list[LinkedInSource] = []
    seen_urls: set[str] = set()

    for row in rows:
        # Đảm bảo mỗi dòng luôn có đủ 12 cột A–L
        padded = row + [""] * (12 - len(row))

        name = padded[0].strip()
        email_1 = padded[1].strip()
        email_2 = padded[2].strip()
        role = padded[3].strip()
        company = padded[4].strip()

        linkedin_url = normalize_linkedin_url(
            padded[5]
        )

        description = padded[6].strip()
        coaching_available = padded[7].strip()
        coaching_method = padded[8].strip()
        coaching_language = padded[9].strip()
        coaching = padded[10].strip()
        location = padded[11].strip()

        # Không có URL LinkedIn hợp lệ thì bỏ qua
        if not linkedin_url:
            continue

        # Không đưa cùng một URL vào danh sách scan hai lần
        if linkedin_url in seen_urls:
            continue

        seen_urls.add(linkedin_url)

        sources.append(
            LinkedInSource(
                name=name or linkedin_url,
                email_1=email_1,
                email_2=email_2,
                role=role,
                company=company,
                linkedin_url=linkedin_url,
                description=description,
                coaching_available=coaching_available,
                coaching_method=coaching_method,
                coaching_language=coaching_language,
                coaching=coaching,
                location=location,
            )
        )

    return sources
