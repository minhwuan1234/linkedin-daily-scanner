from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from playwright.sync_api import (
    BrowserContext,
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from app.linkedin_scanner import (
    LINKEDIN_PROFILE_DIR,
    get_one_enabled_source,
    is_blocked_linkedin_url,
)
from app.settings import Settings


OUTPUT_DIR = Path("output")

BLOCKED_URL_PARTS = (
    "/login",
    "/authwall",
    "/checkpoint",
)

DATE_PATTERN = re.compile(
    r"\b("
    r"present|"
    r"jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|"
    r"january|february|march|april|june|july|august|"
    r"september|october|november|december|"
    r"\d{4}"
    r")\b",
    re.IGNORECASE,
)

DURATION_PATTERN = re.compile(
    r"\b\d+\s*(?:yr|yrs|year|years|mo|mos|month|months)\b",
    re.IGNORECASE,
)


def clean_text(value: str | None) -> str:
    if not value:
        return ""

    lines = [
        " ".join(line.split())
        for line in value.splitlines()
    ]

    return "\n".join(
        line
        for line in lines
        if line
    ).strip()


def clean_single_line(value: str | None) -> str:
    return " ".join(clean_text(value).split())


def remove_duplicate_lines(value: str) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()

    for line in value.splitlines():
        normalized = clean_single_line(line)

        if not normalized:
            continue

        key = normalized.lower()

        if key in seen:
            continue

        seen.add(key)
        output.append(normalized)

    return output


def first_visible_text(
    page: Page,
    selectors: tuple[str, ...],
) -> str:
    for selector in selectors:
        locator = page.locator(selector)

        try:
            count = min(locator.count(), 10)
        except Exception:
            continue

        for index in range(count):
            item = locator.nth(index)

            try:
                if not item.is_visible(timeout=500):
                    continue

                value = clean_single_line(
                    item.inner_text(timeout=2_000)
                )

                if value:
                    return value

            except Exception:
                continue

    return ""


def normalize_profile_url(url: str) -> str:
    parts = urlsplit(url)

    normalized_path = parts.path.rstrip("/") + "/"

    return urlunsplit(
        (
            parts.scheme or "https",
            parts.netloc or "www.linkedin.com",
            normalized_path,
            "",
            "",
        )
    )


def build_detail_url(
    profile_url: str,
    detail_path: str,
) -> str:
    profile_url = normalize_profile_url(profile_url)
    parts = urlsplit(profile_url)

    base_path = parts.path.rstrip("/")

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            f"{base_path}/{detail_path.strip('/')}/",
            "",
            "",
        )
    )


def ensure_linkedin_page_available(page: Page) -> None:
    current_url = page.url.lower()

    if (
        is_blocked_linkedin_url(current_url)
        or any(
            part in current_url
            for part in BLOCKED_URL_PARTS
        )
    ):
        raise RuntimeError(
            "LINKEDIN_SESSION_BLOCKED: "
            f"LinkedIn redirected to {page.url}"
        )


def wait_for_page(page: Page) -> None:
    try:
        page.wait_for_load_state(
            "domcontentloaded",
            timeout=30_000,
        )
    except PlaywrightTimeoutError:
        pass

    page.wait_for_timeout(3_000)


def click_see_more_inside(
    section: Locator,
) -> None:
    button_selectors = (
        "button:has-text('See more')",
        "button:has-text('Show more')",
        "button:has-text('…see more')",
        "button:has-text('...see more')",
    )

    for selector in button_selectors:
        try:
            button = section.locator(selector).first

            if button.is_visible(timeout=500):
                button.click(timeout=2_000)
                return

        except Exception:
            continue


def find_section_by_heading(
    page: Page,
    heading_names: tuple[str, ...],
) -> Locator | None:
    headings = page.locator(
        "main section h2, "
        "main section h3, "
        "main section span[aria-hidden='true']"
    )

    try:
        count = min(headings.count(), 100)
    except Exception:
        return None

    normalized_names = {
        name.lower()
        for name in heading_names
    }

    for index in range(count):
        heading = headings.nth(index)

        try:
            text = clean_single_line(
                heading.inner_text(timeout=1_000)
            ).lower()
        except Exception:
            continue

        if text not in normalized_names:
            continue

        section = heading.locator("xpath=ancestor::section[1]")

        try:
            if section.count() > 0:
                return section.first
        except Exception:
            continue

    return None


def scrape_profile_overview(
    page: Page,
    profile_url: str,
) -> dict[str, Any]:
    page.goto(
        profile_url,
        wait_until="domcontentloaded",
        timeout=60_000,
    )

    wait_for_page(page)
    ensure_linkedin_page_available(page)

    name = first_visible_text(
        page,
        (
            "main h1",
            "h1.text-heading-xlarge",
        ),
    )

    headline = first_visible_text(
        page,
        (
            "main .text-body-medium.break-words",
            "main div.text-body-medium",
            "main section:first-of-type .text-body-medium",
        ),
    )

    location = first_visible_text(
        page,
        (
            "main .text-body-small.inline.t-black--light.break-words",
            "main .pv-text-details__left-panel .text-body-small",
            "main span.text-body-small.inline",
        ),
    )

    followers_count = None
    connections_count = None

    main_text = clean_text(
        page.locator("main").inner_text(
            timeout=15_000
        )
    )

    followers_match = re.search(
        r"([\d,.]+)\s+followers?",
        main_text,
        re.IGNORECASE,
    )

    connections_match = re.search(
        r"([\d,.+]+)\s+connections?",
        main_text,
        re.IGNORECASE,
    )

    if followers_match:
        followers_count = followers_match.group(1)

    if connections_match:
        connections_count = connections_match.group(1)

    return {
        "name": name,
        "linkedin_url": normalize_profile_url(
            profile_url
        ),
        "headline": headline,
        "location": location,
        "followers_count_text": followers_count,
        "connections_count_text": connections_count,
    }


def scrape_about(page: Page) -> str:
    section = find_section_by_heading(
        page,
        ("About",),
    )

    if section is None:
        return ""

    click_see_more_inside(section)
    page.wait_for_timeout(500)

    try:
        raw_text = clean_text(
            section.inner_text(timeout=5_000)
        )
    except Exception:
        return ""

    lines = remove_duplicate_lines(raw_text)

    ignored_lines = {
        "about",
        "see more",
        "show more",
        "…see more",
        "...see more",
    }

    filtered_lines = [
        line
        for line in lines
        if line.lower() not in ignored_lines
    ]

    return "\n".join(filtered_lines).strip()


def looks_like_date_line(line: str) -> bool:
    return bool(
        DATE_PATTERN.search(line)
        and (
            " - " in line
            or "–" in line
            or "·" in line
            or DURATION_PATTERN.search(line)
        )
    )


def split_company_and_employment_type(
    value: str,
) -> tuple[str, str]:
    parts = [
        clean_single_line(part)
        for part in value.split("·")
        if clean_single_line(part)
    ]

    if not parts:
        return "", ""

    company_name = parts[0]
    employment_type = (
        parts[1]
        if len(parts) > 1
        else ""
    )

    return company_name, employment_type


def parse_experience_card(
    card: Locator,
) -> dict[str, Any] | None:
    try:
        raw_text = clean_text(
            card.inner_text(timeout=5_000)
        )
    except Exception:
        return None

    lines = remove_duplicate_lines(raw_text)

    ignored_lines = {
        "experience",
        "show all experiences",
        "see more",
        "show more",
    }

    lines = [
        line
        for line in lines
        if line.lower() not in ignored_lines
    ]

    if not lines:
        return None

    job_title = lines[0]
    company_line = (
        lines[1]
        if len(lines) > 1
        else ""
    )

    company_name, employment_type = (
        split_company_and_employment_type(
            company_line
        )
    )

    date_line = ""
    location = ""

    for index, line in enumerate(lines):
        if not looks_like_date_line(line):
            continue

        date_line = line

        if index + 1 < len(lines):
            candidate_location = lines[index + 1]

            if (
                not looks_like_date_line(
                    candidate_location
                )
                and len(candidate_location) < 160
            ):
                location = candidate_location

        break

    description_start = 2

    if date_line in lines:
        description_start = lines.index(date_line) + 1

        if (
            location
            and description_start < len(lines)
            and lines[description_start] == location
        ):
            description_start += 1

    description_lines = lines[description_start:]

    description = "\n".join(
        description_lines
    ).strip()

    company_linkedin_url = ""

    try:
        links = card.locator(
            "a[href*='linkedin.com/company/']"
        )

        if links.count() > 0:
            company_linkedin_url = (
                links.first.get_attribute("href")
                or ""
            )
    except Exception:
        pass

    date_lower = date_line.lower()

    is_current = (
        "present" in date_lower
        or "current" in date_lower
    )

    return {
        "job_title": job_title,
        "company_name": company_name,
        "employment_type": employment_type,
        "date_text": date_line,
        "location": location,
        "description": description,
        "is_current": is_current,
        "company_linkedin_url": (
            company_linkedin_url
        ),
        "raw_text": raw_text,
    }


def get_experience_cards(page: Page) -> Locator:
    selectors = (
        "main div[data-view-name='profile-component-entity']",
        "main li.pvs-list__paged-list-item",
        "main ul > li",
    )

    for selector in selectors:
        locator = page.locator(selector)

        try:
            if locator.count() > 0:
                return locator
        except Exception:
            continue

    return page.locator(
        "main div[data-view-name='profile-component-entity']"
    )


def scrape_experiences(
    page: Page,
    profile_url: str,
) -> list[dict[str, Any]]:
    experience_url = build_detail_url(
        profile_url,
        "details/experience",
    )

    page.goto(
        experience_url,
        wait_until="domcontentloaded",
        timeout=60_000,
    )

    wait_for_page(page)
    ensure_linkedin_page_available(page)

    for _ in range(4):
        page.mouse.wheel(0, 1_200)
        page.wait_for_timeout(500)

    cards = get_experience_cards(page)

    experiences: list[dict[str, Any]] = []
    seen_raw_texts: set[str] = set()

    try:
        count = min(cards.count(), 100)
    except Exception:
        count = 0

    for index in range(count):
        parsed = parse_experience_card(
            cards.nth(index)
        )

        if not parsed:
            continue

        raw_text = parsed["raw_text"]
        raw_key = clean_single_line(
            raw_text
        ).lower()

        if not raw_key:
            continue

        if raw_key in seen_raw_texts:
            continue

        if len(raw_key) < 5:
            continue

        seen_raw_texts.add(raw_key)
        experiences.append(parsed)

    return experiences


def scrape_profile_raw(
    settings: Settings,
) -> dict[str, Any]:
    source = get_one_enabled_source(settings)

    if not source:
        raise RuntimeError(
            "No enabled LinkedIn source found."
        )

    if not LINKEDIN_PROFILE_DIR.exists():
        raise RuntimeError(
            "LinkedIn browser profile does not exist. "
            "Run create_linkedin_session.py first."
        )

    source_id = int(source["id"])
    profile_url = str(source["linkedin_url"])

    errors: list[dict[str, str]] = []

    with sync_playwright() as playwright:
        context: BrowserContext = (
            playwright.chromium.launch_persistent_context(
                user_data_dir=str(
                    LINKEDIN_PROFILE_DIR.resolve()
                ),
                headless=False,
                viewport={
                    "width": 1440,
                    "height": 1000,
                },
                locale="en-US",
                timezone_id="Asia/Ho_Chi_Minh",
            )
        )

        page = (
            context.pages[0]
            if context.pages
            else context.new_page()
        )

        try:
            profile: dict[str, Any] = {}

            try:
                profile = scrape_profile_overview(
                    page,
                    profile_url,
                )
            except Exception as exc:
                errors.append(
                    {
                        "section": "profile_overview",
                        "message": (
                            f"{type(exc).__name__}: {exc}"
                        ),
                    }
                )

            try:
                profile["about_text"] = scrape_about(
                    page
                )
            except Exception as exc:
                profile["about_text"] = ""

                errors.append(
                    {
                        "section": "about",
                        "message": (
                            f"{type(exc).__name__}: {exc}"
                        ),
                    }
                )

            try:
                experiences = scrape_experiences(
                    page,
                    profile_url,
                )
            except Exception as exc:
                experiences = []

                errors.append(
                    {
                        "section": "experiences",
                        "message": (
                            f"{type(exc).__name__}: {exc}"
                        ),
                    }
                )

            return {
                "source_id": source_id,
                "scraped_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "profile": profile,
                "experiences": experiences,
                "errors": errors,
            }

        finally:
            context.close()
