from __future__ import annotations

import logging
import os
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


logger = logging.getLogger("youtube-browser")


DEFAULT_PROFILE_DIRECTORY = "youtube_browser_profile"


@dataclass(frozen=True)
class YouTubeBrowserSettings:
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
    ) -> "YouTubeBrowserSettings":
        root = (
            project_root
            if project_root is not None
            else Path.cwd()
        )

        profile_value = os.getenv(
            "YOUTUBE_BROWSER_PROFILE_DIR",
            DEFAULT_PROFILE_DIRECTORY,
        ).strip()

        profile_directory = Path(
            profile_value
        )

        if not profile_directory.is_absolute():
            profile_directory = (
                root / profile_directory
            ).resolve()

        return cls(
            profile_directory=profile_directory,
            headless=_read_bool_env(
                "YOUTUBE_HEADLESS",
                default=False,
            ),
            navigation_timeout_ms=_read_int_env(
                "YOUTUBE_NAVIGATION_TIMEOUT_MS",
                default=45_000,
                minimum=5_000,
            ),
            operation_timeout_ms=_read_int_env(
                "YOUTUBE_OPERATION_TIMEOUT_MS",
                default=15_000,
                minimum=1_000,
            ),
            slow_mo_ms=_read_int_env(
                "YOUTUBE_SLOW_MO_MS",
                default=0,
                minimum=0,
            ),
            viewport_width=_read_int_env(
                "YOUTUBE_VIEWPORT_WIDTH",
                default=1440,
                minimum=800,
            ),
            viewport_height=_read_int_env(
                "YOUTUBE_VIEWPORT_HEIGHT",
                default=1000,
                minimum=600,
            ),
        )


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
        parsed_value = int(
            raw_value
        )
    except ValueError as exc:
        raise ValueError(
            f"Invalid integer environment variable "
            f"{key}={raw_value!r}"
        ) from exc

    if parsed_value < minimum:
        raise ValueError(
            f"{key} must be >= {minimum}, "
            f"received {parsed_value}"
        )

    return parsed_value


class YouTubeBrowserManager:
    """
    Quản lý persistent Chromium context cho YouTube.
    """

    def __init__(
        self,
        settings: YouTubeBrowserSettings | None = None,
    ) -> None:
        self.settings = (
            settings
            if settings is not None
            else YouTubeBrowserSettings.from_environment()
        )

        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._started = False

    @property
    def context(
        self,
    ) -> BrowserContext:
        if self._context is None:
            raise RuntimeError(
                "YouTube browser has not been started"
            )

        return self._context

    @property
    def page(
        self,
    ) -> Page:
        if self._page is None:
            raise RuntimeError(
                "YouTube browser has not been started"
            )

        return self._page

    def start(
        self,
    ) -> "YouTubeBrowserManager":
        if self._started:
            return self

        self.settings.profile_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._playwright = sync_playwright().start()

        try:
            self._context = (
                self._playwright.chromium
                .launch_persistent_context(
                    user_data_dir=str(
                        self.settings.profile_directory
                    ),
                    headless=self.settings.headless,
                    slow_mo=self.settings.slow_mo_ms,
                    viewport={
                        "width": (
                            self.settings.viewport_width
                        ),
                        "height": (
                            self.settings.viewport_height
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
            self._playwright.stop()
            self._playwright = None
            raise

        self._context.set_default_timeout(
            self.settings.operation_timeout_ms
        )

        self._context.set_default_navigation_timeout(
            self.settings.navigation_timeout_ms
        )

        pages = self._context.pages

        self._page = (
            pages[0]
            if pages
            else self._context.new_page()
        )

        self._started = True

        return self

    def ensure_page(
        self,
    ) -> Page:
        if not self._started:
            self.start()

        if (
            self._page is None
            or self._page.is_closed()
        ):
            self._page = self.context.new_page()

        return self._page

    def open_youtube(
        self,
    ) -> Page:
        page = self.ensure_page()

        try:
            page.goto(
                "https://www.youtube.com",
                wait_until="domcontentloaded",
                timeout=(
                    self.settings.navigation_timeout_ms
                ),
            )
        except PlaywrightTimeoutError:
            logger.warning(
                "YouTube navigation timed out"
            )

        page.wait_for_timeout(
            2_000
        )

        return page

    def stop(
        self,
    ) -> None:
        if not self._started:
            return

        if self._context is not None:
            try:
                self._context.close()
            except Exception:
                logger.exception(
                    "Could not close YouTube context"
                )

        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                logger.exception(
                    "Could not stop Playwright"
                )

        self._page = None
        self._context = None
        self._playwright = None
        self._started = False

    def __enter__(
        self,
    ) -> "YouTubeBrowserManager":
        return self.start()

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        self.stop()
