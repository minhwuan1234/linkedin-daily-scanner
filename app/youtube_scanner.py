from __future__ import annotations

import re
from urllib.parse import quote_plus, urljoin

from playwright.sync_api import (
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from app.youtube_browser import (
    YouTubeBrowserManager,
)


YOUTUBE_BASE_URL = "https://www.youtube.com"
YOUTUBE_SEARCH_URL = (
    "https://www.youtube.com/results"
    "?search_query={keyword}"
)


def clean_single_line(
    value: str | None,
) -> str:
    return " ".join(
        str(value or "").split()
    ).strip()


def clean_multiline_text(
    value: str | None,
) -> str:
    lines: list[str] = []

    for raw_line in str(value or "").splitlines():
        line = clean_single_line(
            raw_line
        )

        if line:
            lines.append(
                line
            )

    return "\n".join(
        lines
    ).strip()


def clean_channel_name(
    value: str,
) -> str:
    cleaned = clean_single_line(
        value
    )

    prefixes = (
        "Go to channel ",
        "Đi tới kênh ",
    )

    for prefix in prefixes:
        if cleaned.casefold().startswith(
            prefix.casefold()
        ):
            cleaned = cleaned[
                len(prefix):
            ].strip()

    return cleaned


def build_youtube_search_url(
    keyword: str,
) -> str:
    cleaned_keyword = clean_single_line(
        keyword
    )

    if not cleaned_keyword:
        raise ValueError(
            "YouTube search keyword cannot be empty."
        )

    return YOUTUBE_SEARCH_URL.format(
        keyword=quote_plus(
            cleaned_keyword
        )
    )


def normalize_channel_url(
    channel_url: str,
) -> str:
    cleaned_url = clean_single_line(
        channel_url
    )

    if not cleaned_url:
        raise ValueError(
            "Channel URL cannot be empty."
        )

    absolute_url = urljoin(
        YOUTUBE_BASE_URL,
        cleaned_url,
    )

    return (
        absolute_url
        .split("?")[0]
        .rstrip("/")
    )



def ensure_youtube_logged_in(
    browser: YouTubeBrowserManager,
) -> Page:
    """
    Mở YouTube và xác nhận browser profile vẫn còn login.

    Nếu session hết hạn, browser manager sẽ raise:
    YOUTUBE_LOGIN_REQUIRED.
    """

    page = browser.open_youtube_home()

    browser.assert_youtube_logged_in(
        page=page
    )

    print(
        "YouTube login session is ready."
    )

    return page


def search_youtube(
    browser: YouTubeBrowserManager,
    keyword: str,
) -> Page:
    page = browser.ensure_page()

    search_url = build_youtube_search_url(
        keyword
    )

    try:
        page.goto(
            search_url,
            wait_until="domcontentloaded",
            timeout=(
                browser.settings.navigation_timeout_ms
            ),
        )

    except PlaywrightTimeoutError:
        print(
            "YouTube search navigation timed out. "
            "Continuing with current page."
        )

    page.wait_for_timeout(
        3_000
    )

    return page


def apply_this_year_filter(
    page: Page,
) -> None:
    filter_button_selectors = (
        "button[aria-label='Search filters']",
        "button[aria-label='Bộ lọc tìm kiếm']",
        "button:has-text('Filters')",
        "button:has-text('Bộ lọc')",
    )

    filter_opened = False

    for selector in filter_button_selectors:
        try:
            button = page.locator(
                selector
            ).first

            if button.is_visible(
                timeout=2_000
            ):
                button.click(
                    timeout=5_000
                )

                filter_opened = True
                break

        except Exception:
            continue

    if not filter_opened:
        raise RuntimeError(
            "Could not open YouTube search filters."
        )

    page.wait_for_timeout(
        1_500
    )

    target_texts = (
        "This year",
        "Năm nay",
    )

    for target_text in target_texts:
        try:
            exact_text = page.get_by_text(
                target_text,
                exact=True,
            )

            count = min(
                exact_text.count(),
                20,
            )

            for index in range(count):
                item = exact_text.nth(index)

                if not item.is_visible(
                    timeout=1_000
                ):
                    continue

                try:
                    item.click(
                        timeout=5_000
                    )

                except Exception:
                    parent_link = item.locator(
                        "xpath=ancestor::a[1]"
                    )

                    if parent_link.count() > 0:
                        parent_link.click(
                            timeout=5_000
                        )
                    else:
                        item.locator(
                            "xpath=ancestor::"
                            "ytd-search-filter-renderer[1]"
                        ).click(
                            timeout=5_000
                        )

                page.wait_for_timeout(
                    3_000
                )

                print(
                    "Applied YouTube filter: "
                    f"{target_text}"
                )

                return

        except Exception:
            continue

    raise RuntimeError(
        "Could not click YouTube filter: "
        "This year / Năm nay."
    )


def _find_channel_link_in_card(
    card: Locator,
) -> Locator | None:
    selectors = (
        "#channel-info a[href^='/@']",
        "#channel-info a[href*='/channel/']",
        "#channel-info a[href*='/c/']",
        "#channel-info a[href*='/user/']",
        "ytd-channel-name a[href^='/@']",
        "ytd-channel-name a[href*='/channel/']",
        "ytd-channel-name a[href*='/c/']",
        "ytd-channel-name a[href*='/user/']",
    )

    for selector in selectors:
        try:
            candidate = card.locator(
                selector
            ).first

            if (
                candidate.count() > 0
                and candidate.is_visible(
                    timeout=500
                )
            ):
                return candidate

        except Exception:
            continue

    return None


def collect_unique_channels_from_results(
    page: Page,
    *,
    max_channels: int = 3,
) -> list[dict[str, str | int]]:
    target_count = max(
        1,
        int(max_channels),
    )

    channels: list[
        dict[str, str | int]
    ] = []

    seen_channel_urls: set[str] = set()

    unchanged_rounds = 0
    previous_count = 0

    while (
        len(channels) < target_count
        and unchanged_rounds < 6
    ):
        video_cards = page.locator(
            "ytd-video-renderer"
        )

        try:
            card_count = min(
                video_cards.count(),
                200,
            )
        except Exception:
            card_count = 0

        for index in range(card_count):
            card = video_cards.nth(index)

            channel_link = (
                _find_channel_link_in_card(
                    card
                )
            )

            if channel_link is None:
                continue

            try:
                href = clean_single_line(
                    channel_link.get_attribute(
                        "href"
                    )
                )

                if not href:
                    continue

                channel_url = normalize_channel_url(
                    href
                )

                normalized_url = (
                    channel_url.casefold()
                )

                if normalized_url in seen_channel_urls:
                    continue

                channel_name = clean_channel_name(
                    channel_link.get_attribute(
                        "aria-label"
                    )
                    or channel_link.inner_text(
                        timeout=2_000
                    )
                    or ""
                )

                if not channel_name:
                    channel_name_locator = (
                        card.locator(
                            "ytd-channel-name "
                            "yt-formatted-string"
                        ).first
                    )

                    channel_name = clean_channel_name(
                        channel_name_locator.inner_text(
                            timeout=2_000
                        )
                        or ""
                    )

                if not channel_name:
                    continue

                seen_channel_urls.add(
                    normalized_url
                )

                channels.append(
                    {
                        "channel_position": (
                            len(channels) + 1
                        ),
                        "channel_name": channel_name,
                        "channel_url": channel_url,
                    }
                )

                if len(channels) >= target_count:
                    break

            except Exception:
                continue

        if len(channels) == previous_count:
            unchanged_rounds += 1
        else:
            unchanged_rounds = 0

        previous_count = len(
            channels
        )

        if len(channels) >= target_count:
            break

        page.mouse.wheel(
            0,
            1_800,
        )

        page.wait_for_timeout(
            1_200
        )

    return channels


def first_visible_text(
    page: Page,
    selectors: tuple[str, ...],
) -> str:
    for selector in selectors:
        try:
            items = page.locator(
                selector
            )

            count = min(
                items.count(),
                30,
            )

            for index in range(count):
                item = items.nth(index)

                if not item.is_visible(
                    timeout=700
                ):
                    continue

                text = clean_single_line(
                    item.inner_text(
                        timeout=2_000
                    )
                )

                if text:
                    return text

        except Exception:
            continue

    return ""


def _extract_channel_header_text(
    page: Page,
) -> str:
    selectors = (
        "ytd-c4-tabbed-header-renderer",
        "yt-page-header-renderer",
        "#page-header",
        "#channel-header",
        "ytd-browse #header",
    )

    longest_text = ""

    for selector in selectors:
        try:
            items = page.locator(selector)
            count = min(items.count(), 10)

            for index in range(count):
                item = items.nth(index)

                if not item.is_visible(timeout=700):
                    continue

                text = clean_multiline_text(
                    item.inner_text(timeout=3_000)
                )

                if len(text) > len(longest_text):
                    longest_text = text

        except Exception:
            continue

    return longest_text


def _find_metadata_line(
    page: Page,
) -> str:
    selectors = (
        "#channel-handle-and-stats",
        "#channel-handle-and-stats-container",
        "yt-content-metadata-view-model",
        "yt-page-header-view-model "
        "yt-content-metadata-view-model",
        "ytd-c4-tabbed-header-renderer "
        "#subscriber-count",
    )

    candidates: list[str] = []

    for selector in selectors:
        try:
            items = page.locator(selector)
            count = min(items.count(), 20)

            for index in range(count):
                item = items.nth(index)

                if not item.is_visible(timeout=700):
                    continue

                text = clean_single_line(
                    item.inner_text(timeout=2_000)
                )

                if text:
                    candidates.append(text)

        except Exception:
            continue

    header_text = _extract_channel_header_text(
        page
    )

    if header_text:
        candidates.extend(
            clean_single_line(line)
            for line in header_text.splitlines()
            if clean_single_line(line)
        )

    for text in candidates:
        lowered = text.casefold()

        has_subscriber = any(
            marker in lowered
            for marker in (
                "subscriber",
                "subscribers",
                "người đăng ký",
            )
        )

        has_video = bool(
            re.search(
                r"\b[\d.,]+\s*(?:k|m|b|nghìn|tr|triệu)?"
                r"\s*(?:videos?|video)\b",
                lowered,
                re.IGNORECASE,
            )
        )

        if has_subscriber or has_video:
            return text

    return ""


def _split_metadata_parts(
    metadata_text: str,
) -> tuple[str, str]:
    subscriber_count = ""
    video_count = ""

    parts = [
        clean_single_line(part)
        for part in re.split(
            r"[•·]",
            metadata_text,
        )
        if clean_single_line(part)
    ]

    for part in parts:
        lowered = part.casefold()

        if (
            "subscriber" in lowered
            or "subscribers" in lowered
            or "người đăng ký" in lowered
        ):
            subscriber_count = part
            continue

        if re.search(
            r"\bvideos?\b",
            lowered,
            re.IGNORECASE,
        ):
            video_count = part
            continue

    if not subscriber_count:
        match = re.search(
            r"([\d.,]+\s*(?:k|m|b|nghìn|tr|triệu)?"
            r"\s*(?:subscribers?|người đăng ký))",
            metadata_text,
            re.IGNORECASE,
        )

        if match:
            subscriber_count = clean_single_line(
                match.group(1)
            )

    if not video_count:
        match = re.search(
            r"([\d.,]+\s*(?:k|m|b|nghìn|tr|triệu)?"
            r"\s*videos?)",
            metadata_text,
            re.IGNORECASE,
        )

        if match:
            video_count = clean_single_line(
                match.group(1)
            )

    return (
        subscriber_count,
        video_count,
    )


def _click_channel_description_more(
    page: Page,
) -> bool:
    selectors = (
        "yt-description-preview-view-model "
        "button:has-text('more')",
        "yt-description-preview-view-model "
        "button:has-text('xem thêm')",
        "#description-container "
        "button:has-text('more')",
        "#description-container "
        "button:has-text('xem thêm')",
        "button[aria-label='Description']",
        "button[aria-label='Mô tả']",
    )

    for selector in selectors:
        try:
            button = page.locator(selector).first

            if button.is_visible(timeout=1_000):
                button.click(timeout=5_000)
                page.wait_for_timeout(1_500)
                return True

        except Exception:
            continue

    exact_labels = (
        "more",
        "...more",
        "…more",
        "xem thêm",
        "...xem thêm",
        "…xem thêm",
    )

    for label in exact_labels:
        try:
            candidates = page.get_by_text(
                label,
                exact=True,
            )

            count = min(
                candidates.count(),
                20,
            )

            for index in range(count):
                candidate = candidates.nth(index)

                if not candidate.is_visible(timeout=500):
                    continue

                candidate.click(timeout=5_000)
                page.wait_for_timeout(1_500)
                return True

        except Exception:
            continue

    return False


def extract_channel_description(
    page: Page,
) -> str:
    _click_channel_description_more(
        page
    )

    selectors = (
        "ytd-about-channel-renderer "
        "#description-container",
        "ytd-about-channel-renderer "
        "#description",
        "yt-about-channel-view-model "
        "#description-container",
        "yt-about-channel-view-model "
        "#description",
        "[role='dialog'] "
        "#description-container",
        "[role='dialog'] "
        "#description",
        "[role='dialog'] "
        "yt-formatted-string",
        "yt-description-preview-view-model "
        "#description",
        "#description-container",
        "yt-formatted-string#description",
    )

    longest_text = ""

    for selector in selectors:
        try:
            items = page.locator(selector)
            count = min(items.count(), 30)

            for index in range(count):
                item = items.nth(index)

                if not item.is_visible(timeout=700):
                    continue

                text = clean_multiline_text(
                    item.inner_text(timeout=3_000)
                )

                if not text:
                    continue

                lowered = text.casefold()

                if lowered in {
                    "description",
                    "mô tả",
                    "more",
                    "xem thêm",
                }:
                    continue

                if len(text) > len(longest_text):
                    longest_text = text

        except Exception:
            continue

    return longest_text



def clean_youtube_redirect_url(
    url: str,
) -> str:
    """
    Chuyển URL redirect của YouTube về URL đích thật.

    Ví dụ:
    youtube.com/redirect?...&q=https%3A%2F%2Fexample.com
    -> https://example.com
    """

    cleaned = clean_single_line(
        url
    )

    if not cleaned:
        return ""

    try:
        parsed = urlparse(
            cleaned
        )

        if (
            "youtube.com" in parsed.netloc
            and parsed.path == "/redirect"
        ):
            query = parse_qs(
                parsed.query
            )

            target = (
                query.get("q")
                or query.get("url")
            )

            if target:
                return unquote(
                    target[0]
                )

    except Exception:
        return cleaned

    return cleaned


def extract_channel_links(
    page: Page,
) -> list[dict[str, str]]:
    """
    Lấy toàn bộ external links trong popup About của channel.
    """

    dialog = page.locator(
        "[role='dialog']"
    ).last

    try:
        if (
            dialog.count() == 0
            or not dialog.is_visible(
                timeout=1_000
            )
        ):
            return []
    except Exception:
        return []

    links: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    try:
        anchors = dialog.locator(
            "a[href]"
        )

        count = min(
            anchors.count(),
            100,
        )

    except Exception:
        count = 0
        anchors = dialog.locator(
            "a[href]"
        )

    for index in range(
        count
    ):
        anchor = anchors.nth(
            index
        )

        try:
            if not anchor.is_visible(
                timeout=500
            ):
                continue

            href = clean_single_line(
                anchor.get_attribute(
                    "href"
                )
            )

            if not href:
                continue

            absolute_url = urljoin(
                YOUTUBE_BASE_URL,
                href,
            )

            lowered_url = absolute_url.casefold()

            if (
                "youtube.com" in lowered_url
                and "/redirect" not in lowered_url
            ):
                continue

            normalized_url = (
                absolute_url
                .split("#")[0]
                .rstrip("/")
                .casefold()
            )

            if normalized_url in seen_urls:
                continue

            visible_text = clean_single_line(
                anchor.inner_text(
                    timeout=2_000
                )
            )

            container_text = ""

            try:
                container = anchor.locator(
                    "xpath=ancestor::*[self::div or self::li][1]"
                )

                if container.count() > 0:
                    container_text = clean_multiline_text(
                        container.inner_text(
                            timeout=2_000
                        )
                    )

            except Exception:
                container_text = ""

            title = ""

            if container_text:
                lines = [
                    clean_single_line(
                        line
                    )
                    for line in container_text.splitlines()
                    if clean_single_line(
                        line
                    )
                ]

                for line in lines:
                    if line == visible_text:
                        continue

                    if (
                        line.casefold()
                        in absolute_url.casefold()
                    ):
                        continue

                    if (
                        "http://" in line.casefold()
                        or "https://" in line.casefold()
                    ):
                        continue

                    title = line
                    break

            if not title:
                title = visible_text

            if not title:
                title = clean_single_line(
                    anchor.get_attribute(
                        "aria-label"
                    )
                )

            seen_urls.add(
                normalized_url
            )

            links.append(
                {
                    "title": title,
                    "url": absolute_url,
                }
            )

        except Exception:
            continue

    return links



def parse_view_count(
    value: str,
) -> int | None:
    """
    Chuyển text như '82,362,462 views'
    thành số nguyên 82362462.
    """

    digits = re.sub(
        r"[^\d]",
        "",
        value or "",
    )

    if not digits:
        return None

    try:
        return int(
            digits
        )
    except ValueError:
        return None


def extract_channel_more_info(
    page: Page,
) -> dict[str, object]:
    """
    Lấy toàn bộ phần More info và đồng thời tách các trường quen thuộc.

    Kết quả:
    - raw_text
    - email
    - location
    - joined_date
    - total_views
    - channel_id
    - other
    """

    dialog = page.locator(
        "[role='dialog']"
    ).last

    empty_result: dict[str, object] = {
        "raw_text": "",
        "email": "",
        "location": "",
        "joined_date": "",
        "total_views": "",
        "channel_id": "",
        "other": [],
    }

    try:
        if (
            dialog.count() == 0
            or not dialog.is_visible(
                timeout=1_000
            )
        ):
            return empty_result
    except Exception:
        return empty_result

    section_headings = (
        "More info",
        "Thông tin khác",
        "Thông tin thêm",
    )

    heading = None

    for heading_text in section_headings:
        try:
            candidate = dialog.get_by_text(
                heading_text,
                exact=True,
            ).first

            if candidate.is_visible(
                timeout=700
            ):
                heading = candidate
                break

        except Exception:
            continue

    if heading is None:
        return empty_result

    try:
        section_container = heading.locator(
            "xpath=ancestor::*[self::div or self::section][1]"
        )

        if section_container.count() == 0:
            section_container = dialog

    except Exception:
        section_container = dialog

    raw_text = ""

    try:
        raw_text = clean_multiline_text(
            section_container.inner_text(
                timeout=5_000
            )
        )
    except Exception:
        raw_text = ""

    lines = [
        clean_single_line(
            line
        )
        for line in raw_text.splitlines()
        if clean_single_line(
            line
        )
    ]

    heading_names = {
        "more info",
        "thông tin khác",
        "thông tin thêm",
    }

    filtered_lines = [
        line
        for line in lines
        if line.casefold() not in heading_names
    ]

    email = ""
    location = ""
    joined_date = ""
    total_views = ""
    channel_id = ""
    other: list[dict[str, str]] = []

    known_country_names = {
        "united states",
        "united kingdom",
        "canada",
        "australia",
        "india",
        "germany",
        "france",
        "vietnam",
        "viet nam",
        "singapore",
        "netherlands",
        "spain",
        "italy",
        "brazil",
        "mexico",
        "japan",
        "south korea",
    }

    for line in filtered_lines:
        lowered = line.casefold()

        if not email and (
            "email" in lowered
            or "sign in to see email" in lowered
            or "đăng nhập để xem địa chỉ email" in lowered
        ):
            email = line
            continue

        if not joined_date and (
            lowered.startswith("joined ")
            or lowered.startswith("đã tham gia ")
            or lowered.startswith("tham gia ")
        ):
            joined_date = line
            continue

        if not total_views and (
            re.search(
                r"\b[\d.,]+\s+views?\b",
                lowered,
                re.IGNORECASE,
            )
            or "lượt xem" in lowered
        ):
            total_views = line
            continue

        if not channel_id and (
            "youtube.com/@" in lowered
            or "youtube.com/channel/" in lowered
            or "youtube.com/c/" in lowered
            or "youtube.com/user/" in lowered
        ):
            channel_id = line
            continue

        if not location and (
            lowered in known_country_names
            or lowered.startswith("location:")
            or lowered.startswith("địa điểm:")
        ):
            location = line
            continue

        other.append(
            {
                "label": "",
                "value": line,
            }
        )

    return {
        "raw_text": raw_text,
        "email": email,
        "location": location,
        "joined_date": joined_date,
        "total_views": total_views,
        "channel_id": channel_id,
        "other": other,
    }


def extract_channel_about_data(
    page: Page,
) -> dict[str, object]:
    """
    Mở popup About một lần rồi lấy description, links và more info.
    """

    popup_opened = _click_channel_description_more(
        page
    )

    if not popup_opened:
        return {
            "description": "",
            "links": [],
            "more_info": [],
        }

    description = extract_channel_description(
        page
    )

    links = extract_channel_links(
        page
    )

    more_info = extract_channel_more_info(
        page
    )

    return {
        "description": description,
        "links": links,
        "more_info": more_info,
    }


def scan_channel_details(
    browser: YouTubeBrowserManager,
    channel: dict[str, str | int],
) -> dict[str, str | int]:
    page = browser.ensure_page()

    channel_url = normalize_channel_url(
        str(channel["channel_url"])
    )

    try:
        page.goto(
            channel_url,
            wait_until="domcontentloaded",
            timeout=(
                browser.settings.navigation_timeout_ms
            ),
        )

    except PlaywrightTimeoutError:
        print(
            "Channel navigation timed out. "
            "Continuing with current page."
        )

    page.wait_for_timeout(
        3_000
    )

    channel_name = first_visible_text(
        page,
        (
            "yt-page-header-view-model h1",
            "yt-page-header-view-model #channel-name",
            "ytd-c4-tabbed-header-renderer #channel-name",
            "ytd-channel-name #text",
            "h1",
        ),
    )

    if not channel_name:
        channel_name = clean_channel_name(
            str(
                channel.get(
                    "channel_name",
                    "",
                )
            )
        )

    metadata_text = _find_metadata_line(
        page
    )

    (
        subscriber_count,
        video_count,
    ) = _split_metadata_parts(
        metadata_text
    )

    if not subscriber_count:
        subscriber_count = first_visible_text(
            page,
            (
                "#subscriber-count",
                "yt-formatted-string#subscriber-count",
                "span:has-text('subscribers')",
                "span:has-text('subscriber')",
                "span:has-text('người đăng ký')",
            ),
        )

    if not video_count:
        video_count = first_visible_text(
            page,
            (
                "#videos-count",
                "yt-formatted-string#videos-count",
                "span:has-text('videos')",
                "span:has-text('video')",
            ),
        )

    about_data = extract_channel_about_data(
        page
    )

    description = str(
        about_data.get(
            "description",
            "",
        )
    )

    channel_links = about_data.get(
        "links",
        [],
    )

    channel_more_info = about_data.get(
        "more_info",
        [],
    )

    return {
        "channel_position": channel[
            "channel_position"
        ],
        "channel_url": channel_url,
        "channel_name": clean_channel_name(
            channel_name
        ),
        "subscriber_count_text": (
            clean_single_line(
                subscriber_count
            )
        ),
        "video_count_text": (
            clean_single_line(
                video_count
            )
        ),
        "channel_description": description,
        "channel_links": channel_links,
        "channel_more_info_text": str(
            channel_more_info.get(
                "raw_text",
                "",
            )
        )
        if isinstance(
            channel_more_info,
            dict,
        )
        else "",
        "channel_more_info": channel_more_info,
        "email": (
            channel_more_info.get(
                "email",
                "",
            )
            if isinstance(
                channel_more_info,
                dict,
            )
            and "sign in to see email" not in str(
                channel_more_info.get(
                    "email",
                    "",
                )
            ).casefold()
            else ""
        ),
        "email_status": (
            "available"
            if isinstance(
                channel_more_info,
                dict,
            )
            and channel_more_info.get(
                "email",
                "",
            )
            and "sign in to see email" not in str(
                channel_more_info.get(
                    "email",
                    "",
                )
            ).casefold()
            else "login_required"
        ),
        "location": (
            channel_more_info.get(
                "location",
                "",
            )
            if isinstance(
                channel_more_info,
                dict,
            )
            else ""
        ),
        "total_views_text": (
            channel_more_info.get(
                "total_views",
                "",
            )
            if isinstance(
                channel_more_info,
                dict,
            )
            else ""
        ),
        "total_views": parse_view_count(
            str(
                channel_more_info.get(
                    "total_views",
                    "",
                )
            )
        )
        if isinstance(
            channel_more_info,
            dict,
        )
        else None,
        "channel_metadata_text": metadata_text,
    }


def scan_channel_list(
    browser: YouTubeBrowserManager,
    channels: list[
        dict[str, str | int]
    ],
) -> list[dict[str, str | int]]:
    results: list[
        dict[str, str | int]
    ] = []

    for channel in channels:
        print("")
        print(
            "Opening channel:",
            channel["channel_url"],
        )

        try:
            result = scan_channel_details(
                browser=browser,
                channel=channel,
            )

            results.append(
                result
            )

            print(
                "Scanned channel:",
                result["channel_name"],
            )
            print(
                "Subscribers:",
                result[
                    "subscriber_count_text"
                ],
            )
            print(
                "Videos:",
                result[
                    "video_count_text"
                ],
            )
            print(
                "Links:",
                len(
                    result.get(
                        "channel_links",
                        [],
                    )
                ),
            )
            more_info = result.get(
                "channel_more_info",
                {},
            )

            print(
                "More info text length:",
                len(
                    result.get(
                        "channel_more_info_text",
                        "",
                    )
                ),
            )

            if isinstance(
                more_info,
                dict,
            ):
                print(
                    "Joined:",
                    more_info.get(
                        "joined_date",
                        "",
                    ),
                )
                print(
                    "Views:",
                    more_info.get(
                        "total_views",
                        "",
                    ),
                )
                print(
                    "Location:",
                    more_info.get(
                        "location",
                        "",
                    ),
                )

        except Exception as exc:
            print(
                "Could not scan channel "
                f"{channel['channel_url']}: "
                f"{type(exc).__name__}: {exc}"
            )

    return results
