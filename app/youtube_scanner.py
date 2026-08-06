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
    Mở Search filters và chọn Upload date -> This year.
    Hỗ trợ cả tiếng Anh và tiếng Việt.
    """

    filter_button_selectors = (
        "button[aria-label='Search filters']",
        "button[aria-label='Bộ lọc tìm kiếm']",
        "button:has-text('Filters')",
        "button:has-text('Bộ lọc')",
    )

    filter_opened = False

    for selector in filter_button_selectors:
        try:
            button = page.locator(selector).first

            if button.is_visible(timeout=2_000):
                button.click(timeout=5_000)
                filter_opened = True
                break

        except Exception:
            continue

    if not filter_opened:
        raise RuntimeError(
            "Could not open YouTube search filters."
        )

    page.wait_for_timeout(1_500)

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
                            "xpath=ancestor::ytd-search-filter-renderer[1]"
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


def collect_search_videos(
    page: Page,
    *,
    max_results: int = 40,
) -> list[dict[str, str | int]]:
    """
    Scroll trang kết quả và lấy tối đa 40 video đầu tiên.
    """

    target_count = max(
        1,
        min(
            int(max_results),
            40,
        ),
    )

    videos: list[dict[str, str | int]] = []
    seen_urls: set[str] = set()

    unchanged_rounds = 0
    previous_count = 0

    while (
        len(videos) < target_count
        and unchanged_rounds < 6
    ):
        links = page.locator(
            "ytd-video-renderer "
            "a#video-title[href*='/watch']"
        )

        try:
            link_count = min(
                links.count(),
                200,
            )
        except Exception:
            link_count = 0

        for index in range(link_count):
            link = links.nth(index)

            try:
                href = (
                    link.get_attribute("href")
                    or ""
                ).strip()

                if not href:
                    continue

                video_url = urljoin(
                    YOUTUBE_BASE_URL,
                    href,
                )

                if video_url in seen_urls:
                    continue

                title = (
                    link.get_attribute("title")
                    or link.inner_text(
                        timeout=2_000
                    )
                    or ""
                )

                title = " ".join(
                    title.split()
                )

                if not title:
                    continue

                seen_urls.add(
                    video_url
                )

                videos.append(
                    {
                        "video_position": len(videos) + 1,
                        "video_title": title,
                        "video_url": video_url,
                    }
                )

                if len(videos) >= target_count:
                    break

            except Exception:
                continue

        if len(videos) == previous_count:
            unchanged_rounds += 1
        else:
            unchanged_rounds = 0

        previous_count = len(videos)

        if len(videos) >= target_count:
            break

        page.mouse.wheel(
            0,
            2_000,
        )

        page.wait_for_timeout(
            1_200
        )

    return videos
