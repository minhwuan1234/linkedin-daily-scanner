from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import (
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)


logger = logging.getLogger(
    "linkedin-browser"
)


# =========================================================
# CONSTANTS
# =========================================================


DEFAULT_PROFILE_DIRECTORY = (
    "linkedin_browser_profile"
)


LINKEDIN_BLOCKED_URL_PARTS = (
    "/login",
    "/checkpoint",
    "/authwall",
    "/uas/login",
    "/challenge",
)


LINKEDIN_BLOCKED_TEXT_PATTERNS = (
    "sign in",
    "join linkedin",
    "security verification",
    "let’s do a quick verification",
    "lets do a quick verification",
    "verify your identity",
    "unusual activity",
)


# =========================================================
# SETTINGS
# =========================================================


@dataclass(frozen=True)
class LinkedInBrowserSettings:
    profile_directory: Path
    headless: bool
    navigation_timeout_ms: int
    operation_timeout_ms: int
    slow_mo_ms: int
    viewport_width: int
    viewport_height: int

    @classmethod
    def from_environment(
        cls,
        project_root: Path | None = None,
    ) -> "LinkedInBrowserSettings":
        root = (
            project_root
            if project_root is not None
            else Path.cwd()
        )

        profile_directory_value = (
            os.getenv(
                "LINKEDIN_BROWSER_PROFILE_DIR",
                DEFAULT_PROFILE_DIRECTORY,
            )
            .strip()
        )

        profile_directory = Path(
            profile_directory_value
        )

        if not profile_directory.is_absolute():
            profile_directory = (
                root
                / profile_directory
            ).resolve()

        return cls(
            profile_directory=profile_directory,
            headless=_read_bool_env(
                "LINKEDIN_HEADLESS",
                default=False,
            ),
            navigation_timeout_ms=_read_int_env(
                "LINKEDIN_NAVIGATION_TIMEOUT_MS",
                default=45_000,
                minimum=1_000,
            ),
            operation_timeout_ms=_read_int_env(
                "LINKEDIN_OPERATION_TIMEOUT_MS",
                default=15_000,
                minimum=500,
            ),
            slow_mo_ms=_read_int_env(
                "LINKEDIN_SLOW_MO_MS",
                default=0,
                minimum=0,
            ),
            viewport_width=_read_int_env(
                "LINKEDIN_VIEWPORT_WIDTH",
                default=1440,
                minimum=800,
            ),
            viewport_height=_read_int_env(
                "LINKEDIN_VIEWPORT_HEIGHT",
                default=1000,
                minimum=600,
            ),
        )


def _read_bool_env(
    key: str,
    *,
    default: bool,
) -> bool:
    raw_value = os.getenv(
        key
    )

    if raw_value is None:
        return default

    normalized = (
        raw_value
        .strip()
        .lower()
    )

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
        "Invalid boolean environment variable "
        f"{key}={raw_value!r}"
    )


def _read_int_env(
    key: str,
    *,
    default: int,
    minimum: int,
) -> int:
    raw_value = os.getenv(
        key
    )

    if raw_value is None:
        return default

    try:
        parsed_value = int(
            raw_value
        )
    except ValueError as exc:
        raise ValueError(
            "Invalid integer environment variable "
            f"{key}={raw_value!r}"
        ) from exc

    if parsed_value < minimum:
        raise ValueError(
            f"{key} must be >= {minimum}, "
            f"received {parsed_value}"
        )

    return parsed_value


# =========================================================
# TIMEOUT HELPERS
# =========================================================


def _build_deadline(
    timeout_ms: int | None,
) -> float | None:
    if timeout_ms is None:
        return None

    return (
        time.monotonic()
        + (timeout_ms / 1000)
    )


def _remaining_ms(
    deadline: float | None,
    fallback_ms: int,
) -> int:
    if deadline is None:
        return fallback_ms

    remaining = int(
        (
            deadline
            - time.monotonic()
        )
        * 1000
    )

    if remaining <= 0:
        raise LinkedInBrowserTimeoutError(
            "LinkedIn browser operation "
            "exceeded its overall timeout."
        )

    return max(
        1,
        min(
            remaining,
            fallback_ms,
        ),
    )


# =========================================================
# BROWSER MANAGER
# =========================================================


class LinkedInBrowserManager:
    def __init__(
        self,
        settings: LinkedInBrowserSettings | None = None,
    ) -> None:
        self.settings = (
            settings
            if settings is not None
            else LinkedInBrowserSettings.from_environment()
        )

        self._playwright: (
            Playwright | None
        ) = None

        self._context: (
            BrowserContext | None
        ) = None

        self._page: (
            Page | None
        ) = None

        self._started = False

    @property
    def context(
        self,
    ) -> BrowserContext:
        if self._context is None:
            raise RuntimeError(
                "LinkedIn browser has not "
                "been started"
            )

        return self._context

    @property
    def page(
        self,
    ) -> Page:
        if self._page is None:
            raise RuntimeError(
                "LinkedIn browser has not "
                "been started"
            )

        return self._page

    @property
    def is_started(
        self,
    ) -> bool:
        return self._started

    # =====================================================
    # START
    # =====================================================

    def start(
        self,
    ) -> "LinkedInBrowserManager":
        if self._started:
            return self

        self.settings.profile_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        logger.info(
            (
                "Starting LinkedIn browser | "
                "profile_dir=%s | "
                "headless=%s"
            ),
            self.settings.profile_directory,
            self.settings.headless,
        )

        self._playwright = (
            sync_playwright()
            .start()
        )

        try:
            self._context = (
                self._playwright
                .chromium
                .launch_persistent_context(
                    user_data_dir=str(
                        self.settings
                        .profile_directory
                    ),
                    headless=(
                        self.settings.headless
                    ),
                    slow_mo=(
                        self.settings.slow_mo_ms
                    ),
                    viewport={
                        "width": (
                            self.settings
                            .viewport_width
                        ),
                        "height": (
                            self.settings
                            .viewport_height
                        ),
                    },
                    locale="en-US",
                    args=[
                        "--disable-dev-shm-usage",
                        "--no-default-browser-check",
                        "--disable-popup-blocking",
                    ],
                )
            )

        except Exception:
            if self._playwright is not None:
                self._playwright.stop()

            self._playwright = None

            logger.exception(
                "Could not launch persistent "
                "Chromium context"
            )

            raise

        self._context.set_default_timeout(
            self.settings
            .operation_timeout_ms
        )

        self._context.set_default_navigation_timeout(
            self.settings
            .navigation_timeout_ms
        )

        existing_pages = (
            self._context.pages
        )

        if existing_pages:
            self._page = (
                existing_pages[0]
            )
        else:
            self._page = (
                self._context
                .new_page()
            )

        self._started = True

        logger.info(
            "LinkedIn browser started "
            "successfully"
        )

        return self

    # =====================================================
    # PAGE
    # =====================================================

    def ensure_page(
        self,
    ) -> Page:
        if not self._started:
            self.start()

        if (
            self._page is None
            or self._page.is_closed()
        ):
            self._page = (
                self.context
                .new_page()
            )

        return self._page

    # =====================================================
    # OPEN URL
    # =====================================================

    def open_linkedin_url(
        self,
        url: str,
        *,
        wait_until: str = "domcontentloaded",
        overall_timeout_ms: int | None = None,
        raise_on_navigation_timeout: bool = False,
    ) -> Page:
        """
        Open LinkedIn URL.

        overall_timeout_ms=None:
            giữ behavior scanner cũ.

        overall_timeout_ms=...:
            dùng deadline tổng cho caller
            như Connect action.
        """

        cleaned_url = str(
            url or ""
        ).strip()

        if not cleaned_url:
            raise ValueError(
                "LinkedIn URL cannot be empty"
            )

        page = self.ensure_page()

        deadline = _build_deadline(
            overall_timeout_ms
        )

        logger.info(
            "Opening LinkedIn URL: %s",
            cleaned_url,
        )

        navigation_timeout = (
            _remaining_ms(
                deadline,
                self.settings
                .navigation_timeout_ms,
            )
        )

        try:
            page.goto(
                cleaned_url,
                wait_until=wait_until,
                timeout=navigation_timeout,
            )

        except PlaywrightTimeoutError:
            logger.warning(
                "Navigation timeout for %s",
                cleaned_url,
            )

            if raise_on_navigation_timeout:
                raise

        self.wait_for_page_settle(
            page,
            deadline=deadline,
        )

        self.assert_linkedin_session_ready(
            page,
            deadline=deadline,
        )

        return page

    # =====================================================
    # SETTLE
    # =====================================================

    def wait_for_page_settle(
        self,
        page: Page | None = None,
        *,
        timeout_ms: int = 8_000,
        deadline: float | None = None,
    ) -> None:
        active_page = (
            page
            if page is not None
            else self.ensure_page()
        )

        remaining = _remaining_ms(
            deadline,
            timeout_ms,
        )

        try:
            active_page.wait_for_load_state(
                "domcontentloaded",
                timeout=remaining,
            )

        except PlaywrightTimeoutError:
            logger.debug(
                "domcontentloaded wait "
                "timed out"
            )

        # Delay ngắn để UI LinkedIn render.
        remaining = _remaining_ms(
            deadline,
            800,
        )

        delay_ms = min(
            800,
            remaining,
        )

        if delay_ms > 0:
            active_page.wait_for_timeout(
                delay_ms
            )

    # =====================================================
    # SESSION CHECK
    # =====================================================

    def assert_linkedin_session_ready(
        self,
        page: Page | None = None,
        *,
        deadline: float | None = None,
    ) -> None:
        active_page = (
            page
            if page is not None
            else self.ensure_page()
        )

        current_url = (
            active_page.url
            or ""
        ).lower()

        for blocked_path in (
            LINKEDIN_BLOCKED_URL_PARTS
        ):
            if blocked_path in current_url:
                raise LinkedInSessionError(
                    (
                        "LinkedIn session "
                        "requires attention. "
                        "Current URL: "
                        f"{active_page.url}"
                    )
                )

        body_text = ""

        try:
            timeout = _remaining_ms(
                deadline,
                1_500,
            )

            body_text = (
                active_page
                .locator("body")
                .inner_text(
                    timeout=timeout
                )
                .lower()
            )

        except LinkedInBrowserTimeoutError:
            raise

        except Exception:
            logger.debug(
                "Could not read page body "
                "for session check"
            )

        for blocked_text in (
            LINKEDIN_BLOCKED_TEXT_PATTERNS
        ):
            if blocked_text in body_text:
                raise LinkedInSessionError(
                    (
                        "LinkedIn page shows "
                        "a login or verification "
                        "screen. Matched text: "
                        f"{blocked_text!r}"
                    )
                )

    # =====================================================
    # NEW PAGE
    # =====================================================

    def new_page(
        self,
    ) -> Page:
        if not self._started:
            self.start()

        return (
            self.context
            .new_page()
        )

    # =====================================================
    # CLOSE EXTRA PAGES
    # =====================================================

    def close_extra_pages(
        self,
        *,
        keep_page: Page | None = None,
    ) -> None:
        if not self._started:
            return

        page_to_keep = (
            keep_page
            if keep_page is not None
            else self._page
        )

        for page in list(
            self.context.pages
        ):
            if page is page_to_keep:
                continue

            try:
                page.close()

            except Exception:
                logger.debug(
                    "Could not close "
                    "extra page"
                )

    # =====================================================
    # STOP
    # =====================================================

    def stop(
        self,
    ) -> None:
        if not self._started:
            return

        logger.info(
            "Stopping LinkedIn browser"
        )

        if self._context is not None:
            try:
                self._context.close()

            except Exception:
                logger.exception(
                    "Could not close browser "
                    "context cleanly"
                )

        if self._playwright is not None:
            try:
                self._playwright.stop()

            except Exception:
                logger.exception(
                    "Could not stop Playwright "
                    "cleanly"
                )

        self._page = None
        self._context = None
        self._playwright = None
        self._started = False

    def __enter__(
        self,
    ) -> "LinkedInBrowserManager":
        return self.start()

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        self.stop()


# =========================================================
# ERRORS
# =========================================================


class LinkedInBrowserError(
    RuntimeError
):
    pass


class LinkedInBrowserTimeoutError(
    LinkedInBrowserError
):
    pass


class LinkedInSessionError(
    LinkedInBrowserError
):
    pass
