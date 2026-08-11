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
    Click nút dấu ... / More.
    """

    selectors = (
        "button[aria-label='More actions']",
        "button[aria-label*='More actions']",
        "button[aria-label*='More']",
        "button:has-text('More')",
        "button.artdeco-dropdown__trigger",
    )

    return _click_first_visible(
        page,
        selectors,
        timeout_ms=1500,
    )


def _click_connect_in_more_menu(
    page: Page,
) -> bool:
    """
    Sau khi mở dấu ...,
    tìm Connect trong dropdown.
    """

    selectors = (
        "[role='menuitem']:has-text('Connect')",
        "div[role='menu'] li:has-text('Connect')",
        "div[role='menu'] span:has-text('Connect')",
        "li.artdeco-dropdown__item:has-text('Connect')",
        ".artdeco-dropdown__content li:has-text('Connect')",
        ".artdeco-dropdown__content span:has-text('Connect')",
    )

    return _click_first_visible(
        page,
        selectors,
        timeout_ms=2500,
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
        )    timeout_ms: int = 1_500,
) -> bool:
    try:
        return (
            page
            .locator(selector)
            .first
            .is_visible(
                timeout=timeout_ms
            )
        )
    except Exception:
        return False


def _click_first_visible(
    page: Page,
    selectors: tuple[str, ...],
    *,
    timeout_ms: int = 2_000,
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
    )

    return any(
        _is_visible(
            page,
            selector,
        )
        for selector in selectors
    )


def _has_message_action(
    page: Page,
) -> bool:
    selectors = (
        "button:has-text('Message')",
        "a:has-text('Message')",
        "[aria-label^='Message']",
        "[aria-label*='Message']",
    )

    return any(
        _is_visible(
            page,
            selector,
        )
        for selector in selectors
    )


def _click_connect(
    page: Page,
) -> bool:
    direct_selectors = (
        "button:has-text('Connect')",
        "[aria-label^='Invite'][aria-label*='connect']",
        "[aria-label*='Connect']",
    )

    if _click_first_visible(
        page,
        direct_selectors,
    ):
        return True

    more_selectors = (
        "button:has-text('More')",
        "button[aria-label*='More']",
        "[aria-label='More actions']",
    )

    if not _click_first_visible(
        page,
        more_selectors,
    ):
        return False

    page.wait_for_timeout(500)

    menu_connect_selectors = (
        "[role='menuitem']:has-text('Connect')",
        "div[role='menu'] span:has-text('Connect')",
        "li:has-text('Connect')",
    )

    return _click_first_visible(
        page,
        menu_connect_selectors,
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
        timeout_ms=4_000,
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

        page.wait_for_timeout(1_000)

        if _has_pending_state(
            page
        ):
            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="pending",
                message=(
                    "Connection invitation is "
                    "already pending."
                ),
            )

        if _has_message_action(
            page
        ):
            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="already_connected",
                message=(
                    "Profile already appears "
                    "to be connected."
                ),
            )

        connect_clicked = (
            _click_connect(
                page
            )
        )

        if not connect_clicked:
            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="connect_unavailable",
                message=(
                    "Connect action is not "
                    "available on this profile."
                ),
            )

        page.wait_for_timeout(800)

        if _has_pending_state(
            page
        ):
            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="pending",
                message=(
                    "Connection invitation is "
                    "already pending."
                ),
            )

        if not _click_send_without_note(
            page
        ):
            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="failed",
                message=(
                    "Connect was opened but "
                    "'Send without note' "
                    "could not be clicked."
                ),
            )

        page.wait_for_timeout(1_000)

        return LinkedInConnectResult(
            linkedin_url=cleaned_url,
            final_url=page.url,
            status="invitation_sent",
            message=(
                "Connection invitation sent."
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
