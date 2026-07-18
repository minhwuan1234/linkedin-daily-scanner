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

EMPLOYMENT_TYPES = {
    "full-time",
    "part-time",
    "self-employed",
    "freelance",
    "contract",
    "internship",
    "apprenticeship",
    "seasonal",
    "temporary",
    "volunteer",
}

MONTH_PATTERN = (
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|"
    r"may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|"
    r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
)

DATE_RANGE_PATTERN = re.compile(
    rf"\b(?:{MONTH_PATTERN})?\s*\d{{4}}\s*"
    rf"(?:-|–|—|to)\s*"
    rf"(?:present|current|(?:{MONTH_PATTERN})?\s*\d{{4}})\b",
    re.IGNORECASE,
)

DURATION_PATTERN = re.compile(
    r"\b\d+\s*(?:yr|yrs|year|years|mo|mos|month|months)\b",
    re.IGNORECASE,
)

FOLLOWERS_PATTERN = re.compile(
    r"([\d,.]+)\s+followers?",
    re.IGNORECASE,
)

CONNECTIONS_PATTERN = re.compile(
    r"([\d,.+]+)\s+connections?",
    re.IGNORECASE,
)

LOCATION_HINT_PATTERN = re.compile(
    r"\b("
    r"united states|united kingdom|canada|australia|"
    r"india|germany|france|vietnam|viet nam|"
    r"remote|hybrid|on-site|"
    r"greater .* area"
    r")\b",
    re.IGNORECASE,
)


def clean_text(value: str | None) -> str:
    if not value:
        return ""

    lines = [" ".join(line.split()) for line in value.splitlines()]

    return "\n".join(line for line in lines if line).strip()


def clean_single_line(value: str | None) -> str:
    return " ".join(clean_text(value).split())


def unique_lines(value: str) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()

    for line in value.splitlines():
        normalized = clean_single_line(line)

        if not normalized:
            continue

        key = normalized.casefold()

        if key in seen:
            continue

        seen.add(key)
        output.append(normalized)

    return output


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

    if is_blocked_linkedin_url(current_url) or any(
        part in current_url for part in BLOCKED_URL_PARTS
    ):
        raise RuntimeError(
            "LINKEDIN_SESSION_BLOCKED: " f"LinkedIn redirected to {page.url}"
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


def safe_text(
    locator: Locator,
    timeout: int = 2_000,
) -> str:
    try:
        if locator.count() == 0:
            return ""

        return clean_single_line(locator.first.inner_text(timeout=timeout))

    except Exception:
        return ""


def safe_attribute(
    locator: Locator,
    attribute: str,
) -> str:
    try:
        if locator.count() == 0:
            return ""

        return clean_single_line(locator.first.get_attribute(attribute))

    except Exception:
        return ""


def first_visible_text(
    page: Page,
    selectors: tuple[str, ...],
) -> str:
    for selector in selectors:
        locator = page.locator(selector)

        try:
            count = min(locator.count(), 20)
        except Exception:
            continue

        for index in range(count):
            item = locator.nth(index)

            try:
                if not item.is_visible(timeout=500):
                    continue

                value = clean_single_line(item.inner_text(timeout=2_000))

                if value:
                    return value

            except Exception:
                continue

    return ""


def click_see_more_inside(section: Locator) -> None:
    selectors = (
        "button:has-text('See more')",
        "button:has-text('Show more')",
        "button:has-text('…see more')",
        "button:has-text('...see more')",
    )

    for selector in selectors:
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
    normalized_names = {name.casefold() for name in heading_names}

    sections = page.locator("main section")

    try:
        section_count = min(sections.count(), 100)
    except Exception:
        return None

    for index in range(section_count):
        section = sections.nth(index)

        heading_candidates = section.locator(
            "h2, h3, div[role='heading'], " "span[aria-hidden='true']"
        )

        try:
            heading_count = min(
                heading_candidates.count(),
                30,
            )
        except Exception:
            continue

        for heading_index in range(heading_count):
            text = safe_text(heading_candidates.nth(heading_index))

            if text.casefold() in normalized_names:
                return section

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

    top_card = page.locator("main section").first

    name = first_visible_text(
        page,
        (
            "main h1",
            "h1.text-heading-xlarge",
            "main [data-generated-suggestion-target] h1",
        ),
    )

    headline = first_visible_text(
        page,
        (
            "main .text-body-medium.break-words",
            "main div.text-body-medium.break-words",
            "main .pv-text-details__left-panel " ".text-body-medium",
            "main section:first-of-type " "div.text-body-medium",
        ),
    )

    location = first_visible_text(
        page,
        (
            "main .text-body-small.inline." "t-black--light.break-words",
            "main .pv-text-details__left-panel " ".text-body-small",
            "main section:first-of-type " "span.text-body-small.inline",
        ),
    )

    top_card_text = ""

    try:
        top_card_text = clean_text(top_card.inner_text(timeout=10_000))
    except Exception:
        pass

    top_lines = unique_lines(top_card_text)

    ignored_overview_lines = {
        "contact info",
        "message",
        "connect",
        "follow",
        "more",
        "open to",
        "show recruiters you’re open to work",
    }

    filtered_top_lines = [
        line
        for line in top_lines
        if line.casefold() not in ignored_overview_lines
    ]

    if not name:
        for line in filtered_top_lines:
            lower = line.casefold()

            if (
                "followers" in lower
                or "connections" in lower
                or "contact info" in lower
            ):
                continue

            if len(line) <= 120:
                name = line
                break

    if not headline and name:
        try:
            name_index = filtered_top_lines.index(name)
        except ValueError:
            name_index = -1

        if name_index >= 0:
            for line in filtered_top_lines[name_index + 1 :]:
                lower = line.casefold()

                if (
                    "followers" in lower
                    or "connections" in lower
                    or "contact info" in lower
                ):
                    continue

                if len(line) <= 300:
                    headline = line
                    break

    if not location:
        for line in filtered_top_lines:
            if LOCATION_HINT_PATTERN.search(line):
                location = line
                break

    main_text = clean_text(page.locator("main").inner_text(timeout=15_000))

    followers_match = FOLLOWERS_PATTERN.search(main_text)

    connections_match = CONNECTIONS_PATTERN.search(main_text)

    return {
        "name": name,
        "linkedin_url": normalize_profile_url(profile_url),
        "headline": headline,
        "location": location,
        "followers_count_text": (
            followers_match.group(1) if followers_match else None
        ),
        "connections_count_text": (
            connections_match.group(1) if connections_match else None
        ),
        "overview_raw_text": top_card_text,
    }


def scrape_about(page: Page) -> str:
    about_heading = page.get_by_text(
        "About",
        exact=True,
    )

    try:
        heading_count = about_heading.count()
    except Exception:
        return ""

    for index in range(heading_count):
        heading = about_heading.nth(index)

        try:
            if not heading.is_visible(timeout=500):
                continue
        except Exception:
            continue

        section = heading.locator("xpath=ancestor::section[1]")

        try:
            if section.count() == 0:
                continue
        except Exception:
            continue

        click_see_more_inside(section)
        page.wait_for_timeout(700)

        text_candidates = section.locator(
            "div.display-flex.ph5.pv3 "
            "span[aria-hidden='true'], "
            "div.full-width "
            "span[aria-hidden='true'], "
            "span[aria-hidden='true']"
        )

        candidate_values: list[str] = []

        try:
            candidate_count = min(
                text_candidates.count(),
                50,
            )
        except Exception:
            candidate_count = 0

        for candidate_index in range(candidate_count):
            candidate = text_candidates.nth(candidate_index)

            try:
                if not candidate.is_visible(timeout=300):
                    continue

                text = clean_text(candidate.inner_text(timeout=1_500))
            except Exception:
                continue

            if not text:
                continue

            normalized = text.casefold()

            if normalized in {
                "about",
                "see more",
                "show more",
                "… more",
                "... more",
            }:
                continue

            if len(text) < 30:
                continue

            candidate_values.append(text)

        if candidate_values:
            about_text = max(
                candidate_values,
                key=len,
            )

            return (
                about_text.replace("… more", "")
                .replace("... more", "")
                .strip()
            )

        try:
            raw_section_text = clean_text(section.inner_text(timeout=5_000))
        except Exception:
            continue

        lines = unique_lines(raw_section_text)

        filtered_lines: list[str] = []

        for line in lines:
            normalized = line.casefold()

            if normalized in {
                "about",
                "see more",
                "show more",
                "… more",
                "... more",
            }:
                continue

            if normalized in {
                "featured",
                "activity",
                "experience",
                "education",
            }:
                break

            filtered_lines.append(line)

        about_text = "\n".join(filtered_lines).strip()

        if about_text:
            return (
                about_text.replace("… more", "")
                .replace("... more", "")
                .strip()
            )

    return ""


def is_date_line(value: str) -> bool:
    return bool(DATE_RANGE_PATTERN.search(value))


def is_duration_line(value: str) -> bool:
    return bool(DURATION_PATTERN.search(value))


def is_employment_type(value: str) -> bool:
    normalized = value.casefold().strip()

    return normalized in EMPLOYMENT_TYPES


def is_probable_location(value: str) -> bool:
    if not value:
        return False

    if is_date_line(value):
        return False

    if is_duration_line(value):
        return False

    if is_employment_type(value):
        return False

    if len(value) > 160:
        return False

    return bool("," in value or LOCATION_HINT_PATTERN.search(value))


def extract_visible_line_elements(
    container: Locator,
) -> list[dict[str, str]]:
    selectors = (
        "span[aria-hidden='true']",
        "div[aria-hidden='true']",
        "p",
    )

    output: list[dict[str, str]] = []
    seen: set[str] = set()

    for selector in selectors:
        elements = container.locator(selector)

        try:
            count = min(elements.count(), 100)
        except Exception:
            continue

        for index in range(count):
            element = elements.nth(index)

            try:
                if not element.is_visible(timeout=300):
                    continue
            except Exception:
                continue

            text = safe_text(element)

            if not text:
                continue

            key = text.casefold()

            if key in seen:
                continue

            seen.add(key)

            output.append(
                {
                    "text": text,
                    "class": (
                        safe_attribute(
                            element,
                            "class",
                        )
                    ),
                }
            )

    return output


def get_company_url(card: Locator) -> str:
    selectors = (
        "a[href*='/company/']",
        "a[data-field='experience_company_logo']",
    )

    for selector in selectors:
        url = safe_attribute(
            card.locator(selector),
            "href",
        )

        if url:
            return url

    return ""


def get_company_name_from_link(
    card: Locator,
) -> str:
    links = card.locator("a[href*='/company/']")

    try:
        count = min(links.count(), 10)
    except Exception:
        return ""

    for index in range(count):
        link = links.nth(index)

        candidate_selectors = (
            "span[aria-hidden='true']",
            "span",
        )

        for selector in candidate_selectors:
            text = safe_text(link.locator(selector))

            if text and not is_date_line(text) and not is_duration_line(text):
                return text

        text = safe_text(link)

        if text and not is_date_line(text) and not is_duration_line(text):
            return text

    return ""


def classify_experience_lines(
    lines: list[str],
    company_from_link: str,
) -> dict[str, Any]:
    warnings: list[str] = []

    date_text = ""
    duration_text = ""
    employment_type = ""
    location = ""

    semantic_lines: list[str] = []

    for line in lines:
        if not date_text and is_date_line(line):
            date_text = line

            duration_match = DURATION_PATTERN.search(line)

            if duration_match:
                duration_text = duration_match.group(0)

            continue

        if (
            not duration_text
            and is_duration_line(line)
            and not is_date_line(line)
        ):
            duration_text = line
            continue

        if not employment_type and is_employment_type(line):
            employment_type = line
            continue

        if not location and is_probable_location(line):
            location = line
            continue

        semantic_lines.append(line)

    job_title = ""
    company_name = company_from_link

    if semantic_lines:
        job_title = semantic_lines[0]

    if not company_name:
        for candidate in semantic_lines[1:4]:
            if (
                candidate != job_title
                and not is_date_line(candidate)
                and not is_duration_line(candidate)
                and not is_employment_type(candidate)
                and not is_probable_location(candidate)
                and len(candidate) <= 180
            ):
                company_name = candidate
                break

    description_lines: list[str] = []

    for line in semantic_lines:
        if line == job_title:
            continue

        if company_name and line == company_name:
            continue

        if line in {
            employment_type,
            location,
            date_text,
            duration_text,
        }:
            continue

        if len(line) >= 20:
            description_lines.append(line)

    if company_name and is_date_line(company_name):
        warnings.append(
            "Rejected company_name because " "it matched a date pattern."
        )
        company_name = ""

    if employment_type and is_duration_line(employment_type):
        warnings.append(
            "Rejected employment_type because "
            "it matched a duration pattern."
        )
        employment_type = ""

    confidence_score = 0

    if job_title:
        confidence_score += 35

    if company_name:
        confidence_score += 25

    if date_text:
        confidence_score += 20

    if location:
        confidence_score += 10

    if description_lines:
        confidence_score += 10

    return {
        "job_title": job_title,
        "company_name": company_name,
        "employment_type": employment_type,
        "date_text": date_text,
        "duration_text": duration_text,
        "location": location,
        "description": "\n".join(description_lines).strip(),
        "is_current": bool(
            re.search(
                r"\b(present|current)\b",
                date_text,
                re.IGNORECASE,
            )
        ),
        "confidence_score": confidence_score,
        "warnings": warnings,
    }


def parse_experience_card(
    card: Locator,
) -> dict[str, Any] | None:
    try:
        raw_text = clean_text(card.inner_text(timeout=5_000))
    except Exception:
        return None

    if not raw_text:
        return None

    raw_lines = unique_lines(raw_text)

    ignored_lines = {
        "experience",
        "show all experiences",
        "see more",
        "show more",
    }

    raw_lines = [
        line for line in raw_lines if line.casefold() not in ignored_lines
    ]

    if not raw_lines:
        return None

    company_linkedin_url = get_company_url(card)

    company_name = get_company_name_from_link(card)

    date_text = ""
    duration_text = ""
    employment_type = ""
    location = ""

    for line in raw_lines:
        if not date_text and is_date_line(line):
            date_text = line

            duration_match = DURATION_PATTERN.search(line)

            if duration_match:
                duration_text = duration_match.group(0)

            continue

        if not employment_type and is_employment_type(line):
            employment_type = line
            continue

        if not location and is_probable_location(line):
            location = line

    semantic_lines: list[str] = []

    for line in raw_lines:
        if line == date_text:
            continue

        if duration_text and line == duration_text:
            continue

        if employment_type and line == employment_type:
            continue

        if location and line == location:
            continue

        if is_date_line(line):
            continue

        if is_duration_line(line):
            continue

        semantic_lines.append(line)

    job_title = ""

    if semantic_lines:
        job_title = semantic_lines[0]

    if not company_name:
        for candidate in semantic_lines[1:5]:
            if candidate == job_title:
                continue

            if is_date_line(candidate):
                continue

            if is_duration_line(candidate):
                continue

            if is_employment_type(candidate):
                continue

            if is_probable_location(candidate):
                continue

            if len(candidate) > 180:
                continue

            company_name = candidate
            break

    description_lines: list[str] = []

    for line in semantic_lines:
        if line == job_title:
            continue

        if company_name and line == company_name:
            continue

        if len(line) >= 25:
            description_lines.append(line)

    warnings: list[str] = []

    if company_name and is_date_line(company_name):
        warnings.append("company_name matched a date " "and was removed")
        company_name = ""

    if employment_type and is_duration_line(employment_type):
        warnings.append(
            "employment_type matched a " "duration and was removed"
        )
        employment_type = ""

    confidence_score = 0

    if job_title:
        confidence_score += 35

    if company_name:
        confidence_score += 25

    if date_text:
        confidence_score += 20

    if location:
        confidence_score += 10

    if description_lines:
        confidence_score += 10

    if not job_title:
        return None

    return {
        "job_title": job_title,
        "company_name": company_name,
        "employment_type": employment_type,
        "date_text": date_text,
        "duration_text": duration_text,
        "location": location,
        "description": "\n".join(description_lines).strip(),
        "is_current": bool(
            re.search(
                r"\b(present|current)\b",
                date_text,
                re.IGNORECASE,
            )
        ),
        "confidence_score": (confidence_score),
        "warnings": warnings,
        "company_linkedin_url": (company_linkedin_url),
        "raw_lines": raw_lines,
        "raw_text": raw_text,
    }


def get_experience_cards(page: Page) -> Locator:
    selectors = (
        "main div[data-view-name=" "'profile-component-entity']",
        "main li.pvs-list__paged-list-item " "> div",
        "main li.pvs-list__paged-list-item",
    )

    for selector in selectors:
        locator = page.locator(selector)

        try:
            count = locator.count()
        except Exception:
            continue

        if count > 0:
            return locator

    return page.locator(
        "main div[data-view-name=" "'profile-component-entity']"
    )


def find_experience_items(
    page: Page,
) -> Locator:
    selectors = (
        "main " "li.pvs-list__paged-list-item",
        "main " "div[data-view-name=" "'profile-component-entity']",
        "main " "ul.pvs-list > li",
        "main " "section " "ul > li",
    )

    best_locator: Locator | None = None
    best_score = 0

    for selector in selectors:
        locator = page.locator(selector)

        try:
            count = min(
                locator.count(),
                100,
            )
        except Exception:
            continue

        if count == 0:
            continue

        valid_count = 0

        for index in range(count):
            item = locator.nth(index)

            try:
                text = clean_text(item.inner_text(timeout=1_500))
            except Exception:
                continue

            if not text:
                continue

            has_date = bool(DATE_RANGE_PATTERN.search(text))

            has_company_link = False

            try:
                has_company_link = (
                    item.locator("a[href*='/company/']").count() > 0
                )
            except Exception:
                pass

            if has_date or has_company_link:
                valid_count += 1

        if valid_count > best_score:
            best_score = valid_count
            best_locator = locator

    if best_locator is not None:
        return best_locator

    return page.locator("main li.pvs-list__paged-list-item")


def scrape_experience_raw_text(
    page: Page,
    profile_url: str,
) -> str:
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

    try:
        page.wait_for_selector(
            "main",
            timeout=20_000,
        )
    except Exception:
        pass

    previous_height = 0

    for _ in range(12):
        current_height = page.evaluate("document.body.scrollHeight")

        page.mouse.wheel(0, 1_500)
        page.wait_for_timeout(700)

        if current_height == previous_height:
            break

        previous_height = current_height

    page.mouse.wheel(0, -20_000)
    page.wait_for_timeout(800)

    main = page.locator("main")

    try:
        raw_text = clean_text(main.inner_text(timeout=15_000))
    except Exception:
        return ""

    lines = unique_lines(raw_text)

    ignored_exact_lines = {
        "experience",
        "back",
        "home",
        "my network",
        "jobs",
        "messaging",
        "notifications",
        "me",
        "for business",
        "try premium",
        "show all",
        "see more",
        "show more",
    }

    filtered_lines: list[str] = []

    for line in lines:
        normalized = line.casefold()

        if normalized in ignored_exact_lines:
            continue

        if normalized.startswith("skip to "):
            continue

        filtered_lines.append(line)

    return "\n".join(filtered_lines).strip()


def scrape_profile_raw(
    settings: Settings,
) -> dict[str, Any]:
    source = get_one_enabled_source(settings)

    if not source:
        raise RuntimeError("No enabled LinkedIn source found.")

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
                user_data_dir=str(LINKEDIN_PROFILE_DIR.resolve()),
                headless=False,
                viewport={
                    "width": 1440,
                    "height": 1000,
                },
                locale="en-US",
                timezone_id="Asia/Ho_Chi_Minh",
            )
        )

        page = context.pages[0] if context.pages else context.new_page()

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
                        "message": (f"{type(exc).__name__}: " f"{exc}"),
                    }
                )

            try:
                profile["about_text"] = scrape_about(page)
            except Exception as exc:
                profile["about_text"] = ""

                errors.append(
                    {
                        "section": "about",
                        "message": (f"{type(exc).__name__}: " f"{exc}"),
                    }
                )

            try:
                experience_raw_text = scrape_experience_raw_text(
                    page,
                    profile_url,
                )

                if not experience_raw_text:
                    errors.append(
                        {
                            "section": "experience",
                            "message": (
                                "Experience page returned " "no usable text."
                            ),
                        }
                    )
            except Exception as exc:
                experience_raw_text = ""

                errors.append(
                    {
                        "section": "experience",
                        "message": (f"{type(exc).__name__}: " f"{exc}"),
                    }
                )

            return {
                "source_id": source_id,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "profile": profile,
                "experience_raw_text": experience_raw_text,
                "errors": errors,
            }

        finally:
            context.close()
