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
        locator = (
            page
            .locator(selector)
            .first
        )

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
    """
    Thử lần lượt các selector.

    Selector nào visible đầu tiên
    thì click selector đó.
    """

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


# =========================================================
# PROFILE STATE
# =========================================================


def _has_pending_state(
    page: Page,
) -> bool:
    """
    Profile đã được gửi connection invitation
    và đang chờ user accept.

    Pending không phải duplicate database.
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
            timeout_ms=1000,
        )
        for selector in selectors
    )


def _has_first_degree_state(
    page: Page,
) -> bool:
    """
    Kiểm tra dấu hiệu profile đã là
    1st-degree connection.

    Không dùng nút Message để kết luận
    vì profile 2nd / 3rd vẫn có thể có Message.
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
# DIRECT CONNECT
# =========================================================


def _click_direct_connect(
    page: Page,
) -> bool:
    """
    Bước 1:

    Tìm Connect trực tiếp trên header profile.

    Một số profile có nút Connect nằm ngoài
    ngay cạnh Follow / Message.
    """

    selectors = (
        "button:has-text('Connect')",
        "button[aria-label='Connect']",
        "button[aria-label*='Connect']",
        "button[aria-label*='connect']",
        "a:has-text('Connect')",
        "[aria-label^='Invite'][aria-label*='connect']",
    )

    return _click_first_visible(
        page,
        selectors,
        timeout_ms=1500,
    )


# =========================================================
# MORE / ... BUTTON
# =========================================================


def _click_more_button(
    page: Page,
) -> bool:
    """
    Bước 2:

    Nếu không có Connect trực tiếp,
    click nút dấu ...

    DOM thực tế đã inspect:

    <button
        type="button"
        aria-label="More"
        aria-expanded="false"
    >

    Vì vậy dùng aria-label="More"
    thay vì đoán class hoặc SVG.
    """

    try:
        more_button = (
            page
            .locator(
                "button[aria-label='More']"
            )
            .first
        )

        if not more_button.is_visible(
            timeout=2500
        ):
            return False

        more_button.click(
            timeout=2500
        )

        page.wait_for_timeout(500)

        expanded = (
            more_button.get_attribute(
                "aria-expanded"
            )
        )

        print(
            "MORE EXPANDED:",
            expanded,
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
    Sau khi menu ... mở,
    tìm Connect trong dropdown.

    Signal mạnh nhất đã quan sát được:

    href chứa:
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

    fallback_selectors = (
        "[role='menuitem']:has-text('Connect')",
        "a:has-text('Connect')",
        "li:has-text('Connect')",
        "span:has-text('Connect')",
        "div:has-text('Connect')",
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
    Complete Connect discovery flow:

    1. Check Connect trực tiếp.
    2. Nếu không có -> click ...
    3. Tìm Connect trong dropdown.
    """

    print(
        "Checking direct Connect..."
    )

    if _click_direct_connect(
        page
    ):
        print(
            "Direct Connect found."
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
            "More button not found."
        )

        return False

    print(
        "More menu opened."
    )

    page.wait_for_timeout(500)

    print(
        "Looking for Connect "
        "inside More menu..."
    )

    if _click_connect_in_more_menu(
        page
    ):
        print(
            "Connect found in More menu."
        )

        return True

    print(
        "Connect not found "
        "inside More menu."
    )

    return False


# =========================================================
# SEND WITHOUT NOTE
# =========================================================


def _click_send_without_note(
    page: Page,
) -> bool:
    """
    Nếu LinkedIn mở confirmation modal,
    gửi invitation mà không kèm note.
    """

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
# MAIN ACTION
# =========================================================


def connect_profile(
    *,
    browser: LinkedInBrowserManager,
    linkedin_url: str,
) -> LinkedInConnectResult:
    """
    Xử lý Connect cho đúng 1 LinkedIn profile.
    """

    cleaned_url = str(
        linkedin_url or ""
    ).strip()

    if not cleaned_url:
        raise ValueError(
            "linkedin_url cannot be empty"
        )

    try:
        # -------------------------------------------------
        # OPEN PROFILE
        # -------------------------------------------------

        print("")
        print(
            "Opening profile:"
        )
        print(
            cleaned_url
        )

        page = browser.open_linkedin_url(
            cleaned_url
        )

        page.wait_for_timeout(1500)

        # -------------------------------------------------
        # ALREADY PENDING
        # -------------------------------------------------

        if _has_pending_state(
            page
        ):
            print(
                "Profile is already Pending."
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
        # FIND + CLICK CONNECT
        # -------------------------------------------------

        connect_clicked = (
            _click_connect(
                page
            )
        )

        if not connect_clicked:
            # ---------------------------------------------
            # ALREADY CONNECTED
            # ---------------------------------------------

            if _has_first_degree_state(
                page
            ):
                print(
                    "Profile is already "
                    "1st-degree connected."
                )

                return LinkedInConnectResult(
                    linkedin_url=cleaned_url,
                    final_url=page.url,
                    status=(
                        "already_connected"
                    ),
                    message=(
                        "Profile is already a "
                        "1st-degree connection."
                    ),
                )

            # ---------------------------------------------
            # CONNECT NOT AVAILABLE
            # ---------------------------------------------

            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status=(
                    "connect_unavailable"
                ),
                message=(
                    "Connect was not found "
                    "directly or inside "
                    "the More menu."
                ),
            )

        # -------------------------------------------------
        # WAIT AFTER CONNECT CLICK
        # -------------------------------------------------

        page.wait_for_timeout(1000)

        # -------------------------------------------------
        # SOME UI GOES DIRECTLY TO PENDING
        # -------------------------------------------------

        if _has_pending_state(
            page
        ):
            print(
                "Invitation became Pending "
                "immediately."
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
        # CONFIRM MODAL
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

            page.wait_for_timeout(1000)

            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="invitation_sent",
                message=(
                    "Connection invitation sent."
                ),
            )

        # -------------------------------------------------
        # FINAL PENDING CHECK
        # -------------------------------------------------

        page.wait_for_timeout(800)

        if _has_pending_state(
            page
        ):
            print(
                "Invitation confirmed "
                "as Pending."
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
        # CONNECT CLICKED BUT RESULT UNKNOWN
        # -------------------------------------------------

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
        )    timeout_ms: int = 1500,
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
    Click đúng nút dấu ... ở header profile.

    DOM thực tế LinkedIn:
    <button
        type="button"
        aria-label="More"
        aria-expanded="false"
    >
    """

    selectors = (
        "button[aria-label='More']",
        "button[aria-label='More'][aria-expanded='false']",
    )

    return _click_first_visible(
        page,
        selectors,
        timeout_ms=2500,
    ) 
    
page.wait_for_timeout(500)

more_button = page.locator(
    "button[aria-label='More']"
).first

print(
    "MORE EXPANDED:",
    more_button.get_attribute(
        "aria-expanded"
    ),
)

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
