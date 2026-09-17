from __future__ import annotations

import json
from dataclasses import dataclass

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from app.settings import Settings


SHEETS_SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets.readonly"
]


@dataclass
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


def normalize_linkedin_url(value: str) -> str | None:
    value = value.strip()

    if not value:
        return None

    value = value.replace(
        "http://linkedin.com/",
        "https://www.linkedin.com/",
    )
    value = value.replace(
        "https://linkedin.com/",
        "https://www.linkedin.com/",
    )
    value = value.replace(
        "http://www.linkedin.com/",
        "https://www.linkedin.com/",
    )

    if not value.startswith(
        "https://www.linkedin.com/"
    ):
        return None

    if "/in/" not in value and "/company/" not in value:
        return None

    value = value.split("?")[0].split("#")[0].rstrip("/")

    return value + "/"


def get_cell_text(cell: dict) -> str:
    return str(
        cell.get("formattedValue")
        or cell.get("userEnteredValue", {}).get("stringValue")
        or ""
    ).strip()


def get_cell_link(cell: dict) -> str:
    direct_link = cell.get("hyperlink")

    if direct_link:
        return str(direct_link).strip()

    text_format_runs = cell.get("textFormatRuns", [])

    for run in text_format_runs:
        link = (
            run.get("format", {})
            .get("link", {})
            .get("uri")
        )

        if link:
            return str(link).strip()

    return ""


def load_linkedin_sources(
    settings: Settings,
) -> list[LinkedInSource]:
    credentials_info = json.loads(
        settings.google_service_account_json
    )

    credentials = Credentials.from_service_account_info(
        credentials_info,
        scopes=SHEETS_SCOPE,
    )

    service = build(
        "sheets",
        "v4",
        credentials=credentials,
        cache_discovery=False,
    )

    response = (
        service.spreadsheets()
        .get(
            spreadsheetId=settings.google_sheet_id,
            ranges=["Trang tính1!A2:L"],
            includeGridData=True,
            fields=(
                "sheets.data.rowData.values("
                "formattedValue,"
                "userEnteredValue,"
                "hyperlink,"
                "textFormatRuns)"
            ),
        )
        .execute()
    )

    sheets = response.get("sheets", [])

    if not sheets:
        return []

    data_blocks = sheets[0].get("data", [])

    if not data_blocks:
        return []

    rows = data_blocks[0].get("rowData", [])

    sources: list[LinkedInSource] = []
    seen_urls: set[str] = set()

    for row_number, row in enumerate(rows, start=2):
        cells = row.get("values", [])

        def cell_at(index: int) -> dict:
            if index < len(cells):
                return cells[index]
            return {}

        name = get_cell_text(cell_at(0))
        email_1 = get_cell_text(cell_at(1))
        email_2 = get_cell_text(cell_at(2))
        role = get_cell_text(cell_at(3))
        company = get_cell_text(cell_at(4))

        linkedin_cell = cell_at(5)

        linkedin_value = (
            get_cell_link(linkedin_cell)
            or get_cell_text(linkedin_cell)
        )

        linkedin_url = normalize_linkedin_url(
            linkedin_value
        )

        if not linkedin_url:
            print(
                f"Skipped row {row_number}: "
                f"invalid LinkedIn value "
                f"{linkedin_value!r}"
            )
            continue

        if linkedin_url in seen_urls:
            print(
                f"Skipped row {row_number}: "
                f"duplicate URL {linkedin_url}"
            )
            continue

        seen_urls.add(linkedin_url)

        sources.append(
            LinkedInSource(
                name=name,
                email_1=email_1,
                email_2=email_2,
                role=role,
                company=company,
                linkedin_url=linkedin_url,
                description=get_cell_text(cell_at(6)),
                coaching_available=get_cell_text(
                    cell_at(7)
                ),
                coaching_method=get_cell_text(
                    cell_at(8)
                ),
                coaching_language=get_cell_text(
                    cell_at(9)
                ),
                coaching=get_cell_text(cell_at(10)),
                location=get_cell_text(cell_at(11)),
            )
        )

    return sources
