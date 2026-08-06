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
