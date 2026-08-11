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


# =========================================================
# BASIC HELPERS
# =========================================================


def _is_visible(
    page: Page,
    selector: str,
    *,
    timeout_ms: int = 1500,
) -> bool:
    try:
        locator = page.locator(
            selector
        ).first

        return locator.is_visible(
            timeout=timeout_ms
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
            locator = page.locator(
                selector
            ).first

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


# =========================================================
# PROFILE STATE
# =========================================================


def _has_pending_state(
    page: Page,
) -> bool:
    """
    Invitation đã được gửi trước đó
    và đang chờ người nhận accept.
    """

    selectors = (
        "button:has-text('Pending')",
        "button[aria-label*='Pending']",
        "[aria-label*='Pending']",
        "span:has-text('Pending')",
    )

    return any(
        _is_visible(
            page,
            selector,
            timeout_ms=800,
        )
        for selector in selectors
    )


def _has_first_degree_state(
    page: Page,
) -> bool:
    """
    Profile đã là connection 1st degree.

    Không dùng Message làm signal,
    vì profile 2nd/3rd vẫn có thể có Message.
    """

    selectors = (
        "span:has-text('1st')",
        "text=/\\b1st\\b/",
    )

    return any(
        _is_visible(
            page,
            selector,
            timeout_ms=700,
        )
        for selector in selectors
    )


# =========================================================
# CONNECT DIRECTLY ON PROFILE HEADER
# =========================================================


def _click_direct_connect(
    page: Page,
) -> bool:
    """
    Một số profile có Connect
    ngay trên hàng action chính.
    """

    selectors = (
        "button:has-text('Connect')",
        "button[aria-label='Connect']",
        "button[aria-label*='Connect']",
        "button[aria-label*='connect']",
        "a[aria-label*='Connect']",
        "[aria-label^='Invite'][aria-label*='connect']",
    )

    return _click_first_visible(
        page,
        selectors,
        timeout_ms=1200,
    )


# =========================================================
# MORE BUTTON
# =========================================================


def _click_more_button(
    page: Page,
) -> bool:
    """
    DOM thực tế đã inspect:

    <button
        type="button"
        aria-label="More"
        aria-expanded="false"
    >

    Đây là nút dấu ...
    """

    try:
        more_button = page.locator(
            "button[aria-label='More']"
        ).first

        if not more_button.is_visible(
            timeout=2500
        ):
            print(
                "More button is not visible."
            )
            return False

        before = more_button.get_attribute(
            "aria-expanded"
        )

        print(
            "MORE before:",
            before,
        )

        more_button.click(
            timeout=2500
        )

        page.wait_for_timeout(
            600
        )

        after = more_button.get_attribute(
            "aria-expanded"
        )

        print(
            "MORE after:",
            after,
        )

        return True

    except Exception as exc:
        print(
            "MORE BUTTON ERROR:",
            f"{type(exc).__name__}: {exc}",
        )

        return False


# =========================================================
# CONNECT INSIDE MORE MENU
# =========================================================


def _click_connect_in_more_menu(
    page: Page,
) -> bool:
    """
    Sau khi dấu ... được mở,
    tìm action Connect.

    Signal mạnh đã quan sát trên browser:
    href chứa /preload/custom-invite/
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
        print(
            "Connect clicked using invite href."
        )
        return True

    fallback_selectors = (
        "[role='menuitem']:has-text('Connect')",
        "a:has-text('Connect')",
        "li:has-text('Connect')",
        "span:has-text('Connect')",
    )

    if _click_first_visible(
        page,
        fallback_selectors,
        timeout_ms=2000,
    ):
        print(
            "Connect clicked using text fallback."
        )
        return True

    return False


# =========================================================
# COMPLETE CONNECT DISCOVERY
# =========================================================


def _click_connect(
    page: Page,
) -> bool:
    print("")
    print(
        "Checking direct Connect..."
    )

    if _click_direct_connect(
        page
    ):
        print(
            "Direct Connect found and clicked."
        )
        return True

    print(
        "Direct Connect not found."
    )

    print(
        "Opening More menu..."
    )

    if not _click_more_button(
        page
    ):
        print(
            "Could not open More menu."
        )
        return False

    print(
        "More menu opened."
    )

    page.wait_for_timeout(
        500
    )

    print(
        "Looking for Connect in More menu..."
    )

    if _click_connect_in_more_menu(
        page
    ):
        print(
            "Connect found in More menu."
        )
        return True

    print(
        "Connect not found in More menu."
    )

    return False


# =========================================================
# SEND WITHOUT NOTE
# =========================================================


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


# =========================================================
# MAIN CONNECT ACTION
# =========================================================


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
        print("")
        print("=" * 60)
        print("LINKEDIN CONNECT")
        print("=" * 60)
        print(
            f"URL: {cleaned_url}"
        )

        page = browser.open_linkedin_url(
            cleaned_url
        )

        page.wait_for_timeout(
            1500
        )

        # -------------------------------------------------
        # PENDING ALREADY
        # -------------------------------------------------

        if _has_pending_state(
            page
        ):
            print(
                "Result: already pending."
            )

            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="pending",
                message=(
                    "Connection invitation is "
                    "already pending."
                ),
            )

        # -------------------------------------------------
        # FIND CONNECT
        # -------------------------------------------------

        connect_clicked = _click_connect(
            page
        )

        if not connect_clicked:
            # ---------------------------------------------
            # ALREADY CONNECTED
            # ---------------------------------------------

            if _has_first_degree_state(
                page
            ):
                print(
                    "Result: already connected."
                )

                return LinkedInConnectResult(
                    linkedin_url=cleaned_url,
                    final_url=page.url,
                    status="already_connected",
                    message=(
                        "Profile is already a "
                        "1st-degree connection."
                    ),
                )

            # ---------------------------------------------
            # NO CONNECT
            # ---------------------------------------------

            print(
                "Result: Connect unavailable."
            )

            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="connect_unavailable",
                message=(
                    "Connect was not found "
                    "directly or inside "
                    "the More menu."
                ),
            )

        # -------------------------------------------------
        # CONNECT CLICKED
        # -------------------------------------------------

        page.wait_for_timeout(
            1000
        )

        # LinkedIn đôi khi chuyển Pending ngay
        if _has_pending_state(
            page
        ):
            print(
                "Result: invitation sent "
                "(Pending detected)."
            )

            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="invitation_sent",
                message=(
                    "Connection invitation sent."
                ),
            )

        # -------------------------------------------------
        # SEND WITHOUT NOTE
        # -------------------------------------------------

        print(
            "Checking Send without note..."
        )

        if _click_send_without_note(
            page
        ):
            print(
                "Send without note clicked."
            )

            page.wait_for_timeout(
                1000
            )

            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="invitation_sent",
                message=(
                    "Connection invitation sent."
                ),
            )

        # -------------------------------------------------
        # LAST PENDING CHECK
        # -------------------------------------------------

        page.wait_for_timeout(
            800
        )

        if _has_pending_state(
            page
        ):
            print(
                "Result: invitation sent "
                "(final Pending check)."
            )

            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="invitation_sent",
                message=(
                    "Connection invitation sent."
                ),
            )

        # -------------------------------------------------
        # UNKNOWN RESULT
        # -------------------------------------------------

        print(
            "Result: Connect clicked but "
            "confirmation not detected."
        )

        return LinkedInConnectResult(
            linkedin_url=cleaned_url,
            final_url=page.url,
            status="failed",
            message=(
                "Connect was clicked, but "
                "no Pending state or "
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
