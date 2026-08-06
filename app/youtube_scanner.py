from __future__ import annotations

from urllib.parse import quote_plus

from playwright.sync_api import (
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from app.youtube_browser import (
    YouTubeBrowserManager,
)


YOUTUBE_SEARCH_URL = (
    "https://www.youtube.com/results"
    "?search_query={keyword}"
)


def build_youtube_search_url(
    keyword: str,
) -> str:
    cleaned_keyword = " ".join(
        str(keyword or "").split()
    )

    if not cleaned_keyword:
        raise ValueError(
            "YouTube search keyword cannot be empty"
        )

    return YOUTUBE_SEARCH_URL.format(
        keyword=quote_plus(cleaned_keyword)
    )


def search_youtube(
    browser: YouTubeBrowserManager,
    keyword: str,
) -> Page:
    """
    Mở trang kết quả tìm kiếm YouTube theo keyword.
    """

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
    """
    Mở bộ lọc tìm kiếm YouTube và chọn:
    Ngày tải lên -> Năm nay.
    """

    filter_button_selectors = (
        "button[aria-label='Bộ lọc tìm kiếm']",
        "button[aria-label='Search filters']",
        "button:has-text('Bộ lọc')",
        "button:has-text('Filters')",
        "yt-button-shape button:has-text('Bộ lọc')",
        "yt-button-shape button:has-text('Filters')",
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
        1_000
    )

    this_year_selectors = (
        "ytd-search-filter-renderer:has-text('Năm nay')",
        "yt-formatted-string:text-is('Năm nay')",
        "a:has-text('Năm nay')",
        "ytd-search-filter-renderer:has-text('This year')",
        "yt-formatted-string:text-is('This year')",
        "a:has-text('This year')",
    )

    for selector in this_year_selectors:
        try:
            option = page.locator(
                selector
            ).first

            if option.is_visible(
                timeout=2_000
            ):
                option.click(
                    timeout=5_000
                )

                page.wait_for_timeout(
                    3_000
                )

                return

        except Exception:
            continue

    raise RuntimeError(
        "Could not apply YouTube filter: Năm nay."
    )
