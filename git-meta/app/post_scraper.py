from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Any

from playwright.sync_api import (
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from app.linkedin_browser import (
    LinkedInBrowserManager,
    LinkedInSessionError,
)


logger = logging.getLogger("linkedin-post-scraper")


# =========================================================
# ENV HELPERS
# =========================================================

def _read_bool_env(
    key: str,
    *,
    default: bool,
) -> bool:
    raw_value = os.getenv(key)

    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()

    if normalized in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }:
        return True

    if normalized in {
        "0",
        "false",
        "no",
        "n",
        "off",
    }:
        return False

    raise ValueError(
        f"Invalid boolean environment variable "
        f"{key}={raw_value!r}"
    )


def _read_int_env(
    key: str,
    *,
    default: int,
    minimum: int,
) -> int:
    raw_value = os.getenv(key)

    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(
            f"Invalid integer environment variable "
            f"{key}={raw_value!r}"
        ) from exc

    if value < minimum:
        raise ValueError(
            f"{key} must be >= {minimum}, "
            f"received {value}"
        )

    return value


# =========================================================
# SETTINGS
# =========================================================

@dataclass(frozen=True)
class PostScraperSettings:
    enabled: bool
    max_posts: int
    scroll_attempts: int
    scroll_delay_ms: int
    load_timeout_ms: int

    @classmethod
    def from_environment(
        cls,
    ) -> "PostScraperSettings":
        return cls(
            enabled=_read_bool_env(
                "LINKEDIN_SCAN_POSTS",
                default=True,
            ),
            max_posts=_read_int_env(
                "LINKEDIN_MAX_POSTS",
                default=5,
                minimum=1,
            ),
            scroll_attempts=_read_int_env(
                "LINKEDIN_POST_SCROLL_ATTEMPTS",
                default=8,
                minimum=1,
            ),
            scroll_delay_ms=_read_int_env(
                "LINKEDIN_POST_SCROLL_DELAY_MS",
                default=1500,
                minimum=100,
            ),
            load_timeout_ms=_read_int_env(
                "LINKEDIN_POST_LOAD_TIMEOUT_MS",
                default=20000,
                minimum=1000,
            ),
        )


# =========================================================
# SELECTORS
# =========================================================

POST_CONTAINER_SELECTORS = (
    "div.feed-shared-update-v2",
    "div[data-urn*='activity']",
    "article",
)

CAPTION_SELECTORS = (
    "div.update-components-text",
    "div.feed-shared-update-v2__description",
    "div.feed-shared-inline-show-more-text",
    "span.break-words",
    "div[dir='ltr']",
)


# =========================================================
# HELPERS
# =========================================================

def _clean_text(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(value)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    return text or None


def _safe_inner_text(
    locator: Locator,
    *,
    timeout_ms: int = 2500,
) -> str | None:
    try:
        return _clean_text(
            locator.inner_text(
                timeout=timeout_ms,
            )
        )
    except Exception:
        return None


def _first_caption_from_container(
    container: Locator,
) -> str | None:
    for selector in CAPTION_SELECTORS:
        try:
            locator = container.locator(selector).first

            if locator.count() == 0:
                continue

            text = _safe_inner_text(locator)

            if text:
                return text
        except Exception:
            continue

    return None


# =========================================================
# SCRAPER
# =========================================================

class LinkedInPostScraper:
    """
    Chỉ lấy caption của tối đa N bài gần nhất.

    Không lấy:
    - post URL
    - published time
    - reactions
    - comments
    - reposts
    - author
    """

    def __init__(
        self,
        browser: LinkedInBrowserManager,
        settings: PostScraperSettings | None = None,
    ) -> None:
        self.browser = browser
        self.settings = (
            settings
            if settings is not None
            else PostScraperSettings.from_environment()
        )

    def scan_profile_post_captions(
        self,
        profile_url: str,
    ) -> list[str]:
        if not self.settings.enabled:
            logger.info(
                "LinkedIn post scanning is disabled"
            )
            return []

        posts_url = self._build_posts_url(
            profile_url
        )

        logger.info(
            "Scanning LinkedIn post captions: %s",
            posts_url,
        )

        try:
            page = self.browser.open_linkedin_url(
                posts_url
            )
        except LinkedInSessionError:
            raise
        except Exception:
            logger.exception(
                "Could not open LinkedIn posts page"
            )
            return []

        self._wait_for_posts(page)
        self._expand_visible_post_text(page)
        self._scroll_until_enough_posts(page)
        self._expand_visible_post_text(page)

        captions = self._extract_captions(page)

        logger.info(
            "Post caption scan complete | count=%s",
            len(captions),
        )

        return captions

    def _build_posts_url(
        self,
        profile_url: str,
    ) -> str:
        cleaned = profile_url.strip().rstrip("/")

        if "/in/" not in cleaned:
            raise ValueError(
                "Post scan only supports LinkedIn profile URLs"
            )

        return (
            f"{cleaned}/recent-activity/all/"
        )

    def _wait_for_posts(
        self,
        page: Page,
    ) -> None:
        selector = ", ".join(
            POST_CONTAINER_SELECTORS
        )

        try:
            page.locator(selector).first.wait_for(
                state="attached",
                timeout=self.settings.load_timeout_ms,
            )
        except PlaywrightTimeoutError:
            logger.warning(
                "No post container detected before timeout"
            )

            self.browser.assert_linkedin_session_ready(
                page
            )

    def _find_post_containers(
        self,
        page: Page,
    ) -> Locator:
        for selector in POST_CONTAINER_SELECTORS:
            locator = page.locator(selector)

            try:
                if locator.count() > 0:
                    return locator
            except Exception:
                continue

        return page.locator(
            POST_CONTAINER_SELECTORS[0]
        )

    def _scroll_until_enough_posts(
        self,
        page: Page,
    ) -> None:
        previous_count = 0
        stable_rounds = 0

        for attempt in range(
            self.settings.scroll_attempts
        ):
            containers = self._find_post_containers(
                page
            )

            try:
                current_count = containers.count()
            except Exception:
                current_count = 0

            logger.info(
                (
                    "Post scroll attempt %s/%s | "
                    "current_count=%s"
                ),
                attempt + 1,
                self.settings.scroll_attempts,
                current_count,
            )

            if current_count >= self.settings.max_posts:
                return

            if current_count <= previous_count:
                stable_rounds += 1
            else:
                stable_rounds = 0

            if stable_rounds >= 3:
                return

            previous_count = current_count

            page.evaluate(
                """
                () => {
                    window.scrollBy({
                        top: Math.max(
                            window.innerHeight * 0.85,
                            700
                        ),
                        behavior: "smooth"
                    });
                }
                """
            )

            page.wait_for_timeout(
                self.settings.scroll_delay_ms
            )

            self.browser.assert_linkedin_session_ready(
                page
            )

    def _expand_visible_post_text(
        self,
        page: Page,
    ) -> None:
        selectors = (
            "button:has-text('see more')",
            "button:has-text('See more')",
            "button:has-text('…more')",
            "button[aria-label*='see more' i]",
            "button[aria-label*='show more' i]",
        )

        for selector in selectors:
            try:
                buttons = page.locator(selector)
                count = min(
                    buttons.count(),
                    self.settings.max_posts * 2,
                )
            except Exception:
                continue

            for index in range(count):
                try:
                    button = buttons.nth(index)

                    if not button.is_visible():
                        continue

                    button.click(
                        timeout=2000,
                    )

                    page.wait_for_timeout(250)
                except Exception:
                    continue

    def _extract_captions(
        self,
        page: Page,
    ) -> list[str]:
        containers = self._find_post_containers(
            page
        )

        captions: list[str] = []
        seen: set[str] = set()

        try:
            container_count = containers.count()
        except Exception:
            container_count = 0

        max_candidates = min(
            container_count,
            self.settings.max_posts * 3,
        )

        for index in range(max_candidates):
            if len(captions) >= self.settings.max_posts:
                break

            container = containers.nth(index)

            caption = _first_caption_from_container(
                container
            )

            if not caption:
                continue

            normalized = caption.strip().lower()

            if normalized in seen:
                continue

            seen.add(normalized)
            captions.append(caption)

        return captions


# =========================================================
# PUBLIC FUNCTION
# =========================================================

def scan_recent_post_captions(
    *,
    browser: LinkedInBrowserManager,
    profile_url: str,
    settings: PostScraperSettings | None = None,
) -> list[str]:
    scraper = LinkedInPostScraper(
        browser=browser,
        settings=settings,
    )

    return scraper.scan_profile_post_captions(
        profile_url
    )
