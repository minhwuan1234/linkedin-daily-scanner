from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from playwright.sync_api import (
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from app.linkedin_browser import (
    LinkedInBrowserManager,
)


ConnectStatus = Literal[
    "invitation_sent",
    "pending",
    "already_connected",
    "connect_unavailable",
    "failed",
]


@dataclass(frozen=True)
class LinkedInConnectResult:
    linkedin_url: str
    final_url: str
    status: ConnectStatus
    message: str


def _is_visible(
    page: Page,
    selector: str,
    *,
    timeout_ms: int = 1500,
) -> bool:
    try:
        return (
            page
            .locator(selector)
            .first
            .is_visible(timeout=timeout_ms)
        )
    except Exception:
        return False


def _click_first_visible(
    page: Page,
    selectors: tuple[str, ...],
    *,
    timeout_ms: int = 2000,
) -> bool:
    for selector in selectors:
        try:
            locator = (
                page
                .locator(selector)
                .first
            )

            if not locator.is_visible(
                timeout=timeout_ms
            ):
                continue

            locator.click(
                timeout=timeout_ms
            )

            return True

        except Exception:
            continue

    return False


def _has_pending_state(
    page: Page,
) -> bool:
    selectors = (
        "button:has-text('Pending')",
        "[aria-label*='Pending']",
        "button[aria-label*='Pending']",
        "span:has-text('Pending')",
    )

    return any(
        _is_visible(
            page,
            selector,
        )
        for selector in selectors
    )


def _has_first_degree_state(
    page: Page,
) -> bool:
    """
    Dùng 1st-degree để xác định
    profile đã connected.

    Không dùng Message để kết luận.
    """

    selectors = (
        "text=/\\b1st\\b/",
        "span:has-text('1st')",
    )

    return any(
        _is_visible(
            page,
            selector,
            timeout_ms=700,
        )
        for selector in selectors
    )


def _click_direct_connect(
    page: Page,
) -> bool:
    """
    Ưu tiên tìm Connect ngay trên header.
    """

    selectors = (
        "button:has-text('Connect')",
        "button[aria-label*='Connect']",
        "button[aria-label*='connect']",
        "[aria-label^='Invite'][aria-label*='connect']",
    )

    return _click_first_visible(
        page,
        selectors,
        timeout_ms=1500,
    )

def _click_more_button(
    page: Page,
) -> bool:
    """
    Tìm nút dấu ... thông qua SVG overflow
    rồi click button cha chứa icon đó.
    """

    try:
        overflow_icon = (
            page
            .locator(
                "svg#overflow-web-ios-small"
            )
            .first
        )

        if not overflow_icon.is_visible(
            timeout=2000
        ):
            return False

        button = overflow_icon.locator(
            "xpath=ancestor::button[1]"
        )

        if not button.is_visible(
            timeout=1500
        ):
            return False

        button.click(
            timeout=2000
        )

        return True

    except Exception:
        return False

def _click_connect_in_more_menu(
    page: Page,
) -> bool:
    """
    Sau khi mở dấu ...,
    ưu tiên bắt Connect bằng URL action thực tế
    của LinkedIn.

    Screenshot thực tế cho thấy Connect trỏ tới:
    /preload/custom-invite/
    """

    strong_selectors = (
        "a[href*='/preload/custom-invite/']",
        "a[href*='preload/custom-invite']",
    )

    if _click_first_visible(
        page,
        strong_selectors,
        timeout_ms=2500,
    ):
        return True

    # Fallback theo text nếu LinkedIn đổi href
    fallback_selectors = (
        "[role='menuitem']:has-text('Connect')",
        "a:has-text('Connect')",
        "li:has-text('Connect')",
        "span:has-text('Connect')",
    )

    return _click_first_visible(
        page,
        fallback_selectors,
        timeout_ms=2000,
    )


def _click_connect(
    page: Page,
) -> bool:
    """
    Flow:

    1. Tìm Connect trực tiếp.
    2. Nếu không thấy -> mở ...
    3. Tìm Connect trong menu.
    """

    if _click_direct_connect(page):
        return True

    if not _click_more_button(page):
        return False

    page.wait_for_timeout(600)

    return _click_connect_in_more_menu(
        page
    )


def _click_send_without_note(
    page: Page,
) -> bool:
    selectors = (
        "button:has-text('Send without a note')",
        "button:has-text('Send without note')",
        "button[aria-label*='Send without']",
    )

    return _click_first_visible(
        page,
        selectors,
        timeout_ms=3000,
    )


def connect_profile(
    *,
    browser: LinkedInBrowserManager,
    linkedin_url: str,
) -> LinkedInConnectResult:
    cleaned_url = str(
        linkedin_url or ""
    ).strip()

    if not cleaned_url:
        raise ValueError(
            "linkedin_url cannot be empty"
        )

    try:
        page = browser.open_linkedin_url(
            cleaned_url
        )

        page.wait_for_timeout(1000)

        # Đã gửi invite rồi
        if _has_pending_state(page):
            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="pending",
                message=(
                    "Connection invitation is "
                    "already pending."
                ),
            )

        # Luôn tìm Connect trước
        connect_clicked = (
            _click_connect(page)
        )

        if not connect_clicked:
            # Không có Connect và là 1st
            # => đã connected
            if _has_first_degree_state(
                page
            ):
                return LinkedInConnectResult(
                    linkedin_url=cleaned_url,
                    final_url=page.url,
                    status="already_connected",
                    message=(
                        "Profile is already a "
                        "1st-degree connection."
                    ),
                )

            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="connect_unavailable",
                message=(
                    "Connect was not found "
                    "in the header or More menu."
                ),
            )

        page.wait_for_timeout(800)

        # Có UI LinkedIn click Connect
        # xong chuyển Pending ngay
        if _has_pending_state(page):
            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="invitation_sent",
                message=(
                    "Connection invitation sent."
                ),
            )

        # Nếu có popup confirm
        if _click_send_without_note(
            page
        ):
            page.wait_for_timeout(800)

            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="invitation_sent",
                message=(
                    "Connection invitation sent."
                ),
            )

        # Check Pending thêm lần nữa
        page.wait_for_timeout(700)

        if _has_pending_state(page):
            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="invitation_sent",
                message=(
                    "Connection invitation sent."
                ),
            )

        return LinkedInConnectResult(
            linkedin_url=cleaned_url,
            final_url=page.url,
            status="failed",
            message=(
                "Connect was clicked, "
                "but no Pending state or "
                "Send without note confirmation "
                "was detected."
            ),
        )

    except PlaywrightTimeoutError as exc:
        return LinkedInConnectResult(
            linkedin_url=cleaned_url,
            final_url="",
            status="failed",
            message=(
                "LinkedIn action timed out: "
                f"{exc}"
            ),
        )

    except Exception as exc:
        return LinkedInConnectResult(
            linkedin_url=cleaned_url,
            final_url="",
            status="failed",
            message=(
                f"{type(exc).__name__}: {exc}"
            ),
        )
