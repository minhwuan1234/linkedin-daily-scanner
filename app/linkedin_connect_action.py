from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

from playwright.sync_api import (
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from app.linkedin_browser import (
    LinkedInBrowserManager,
    LinkedInBrowserTimeoutError,
    LinkedInSessionError,
)


# =========================================================
# CONSTANTS
# =========================================================


PROFILE_TIMEOUT_MS = 10_000


ConnectStatus = Literal[
    "invitation_sent",
    "pending",
    "already_connected",
    "connect_unavailable",
    "failed",
]


# =========================================================
# RESULT
# =========================================================


@dataclass(frozen=True)
class LinkedInConnectResult:
    linkedin_url: str
    final_url: str
    status: ConnectStatus
    message: str


# =========================================================
# TIMEOUT
# =========================================================


class LinkedInProfileActionTimeout(
    RuntimeError
):
    pass


def _build_deadline() -> float:
    return (
        time.monotonic()
        + (
            PROFILE_TIMEOUT_MS
            / 1000
        )
    )


def _remaining_ms(
    deadline: float,
    *,
    maximum_ms: int,
) -> int:
    remaining = int(
        (
            deadline
            - time.monotonic()
        )
        * 1000
    )

    if remaining <= 0:
        raise LinkedInProfileActionTimeout(
            "Profile processing exceeded "
            "the 10 second limit."
        )

    return max(
        1,
        min(
            remaining,
            maximum_ms,
        ),
    )


def _check_deadline(
    deadline: float,
) -> None:
    if time.monotonic() >= deadline:
        raise LinkedInProfileActionTimeout(
            "Profile processing exceeded "
            "the 10 second limit."
        )


# =========================================================
# BASIC HELPERS
# =========================================================


def _is_visible(
    page: Page,
    selector: str,
    *,
    deadline: float,
    maximum_ms: int = 600,
) -> bool:
    _check_deadline(
        deadline
    )

    try:
        timeout = _remaining_ms(
            deadline,
            maximum_ms=maximum_ms,
        )

        locator = (
            page
            .locator(selector)
            .first
        )

        return locator.is_visible(
            timeout=timeout
        )

    except LinkedInProfileActionTimeout:
        raise

    except Exception:
        return False


def _click_first_visible(
    page: Page,
    selectors: tuple[str, ...],
    *,
    deadline: float,
    maximum_ms: int = 900,
) -> bool:
    for selector in selectors:
        _check_deadline(
            deadline
        )

        try:
            locator = (
                page
                .locator(selector)
                .first
            )

            timeout = _remaining_ms(
                deadline,
                maximum_ms=maximum_ms,
            )

            if not locator.is_visible(
                timeout=timeout
            ):
                continue

            timeout = _remaining_ms(
                deadline,
                maximum_ms=maximum_ms,
            )

            locator.click(
                timeout=timeout
            )

            return True

        except LinkedInProfileActionTimeout:
            raise

        except Exception:
            continue

    return False


# =========================================================
# PROFILE NOT FOUND
# =========================================================


def _is_profile_not_found(
    page: Page,
    *,
    deadline: float,
) -> bool:
    """
    Detect URL/profile không tồn tại.

    Trường hợp này vẫn tính FAILED
    ở cấp job, nhưng worker sẽ chuyển
    ngay sang profile tiếp theo.
    """

    current_url = (
        page.url
        or ""
    ).lower()

    url_signals = (
        "/404",
        "/error",
    )

    if any(
        signal in current_url
        for signal in url_signals
    ):
        return True

    try:
        timeout = _remaining_ms(
            deadline,
            maximum_ms=700,
        )

        body_text = (
            page
            .locator("body")
            .inner_text(
                timeout=timeout
            )
            .lower()
        )

    except LinkedInProfileActionTimeout:
        raise

    except Exception:
        return False

    text_signals = (
        "this page doesn’t exist",
        "this page doesn't exist",
        "page not found",
        "profile not found",
        "this profile is not available",
        "the profile you requested does not exist",
    )

    return any(
        signal in body_text
        for signal in text_signals
    )


# =========================================================
# PENDING
# =========================================================


def _has_pending_state(
    page: Page,
    *,
    deadline: float,
) -> bool:
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
            deadline=deadline,
            maximum_ms=350,
        )
        for selector in selectors
    )


# =========================================================
# ALREADY CONNECTED
# =========================================================


def _has_first_degree_state(
    page: Page,
    *,
    deadline: float,
) -> bool:
    """
    Chỉ chấp nhận 1st trong vùng
    header của profile.

    Không dùng Message làm signal.
    """

    _check_deadline(
        deadline
    )

    try:
        candidates = (
            page
            .get_by_text(
                "1st",
                exact=True,
            )
        )

        count = (
            candidates.count()
        )

        for index in range(
            count
        ):
            _check_deadline(
                deadline
            )

            candidate = (
                candidates
                .nth(index)
            )

            try:
                timeout = _remaining_ms(
                    deadline,
                    maximum_ms=300,
                )

                if not candidate.is_visible(
                    timeout=timeout
                ):
                    continue

                box = (
                    candidate
                    .bounding_box()
                )

                if not box:
                    continue

                if box["y"] <= 550:
                    print(
                        "1ST DEGREE signal:",
                        "y=",
                        box["y"],
                    )

                    return True

            except LinkedInProfileActionTimeout:
                raise

            except Exception:
                continue

    except LinkedInProfileActionTimeout:
        raise

    except Exception:
        pass

    return False


# =========================================================
# DIRECT CONNECT
# =========================================================


def _click_direct_connect(
    page: Page,
    *,
    deadline: float,
) -> bool:
    """
    STEP 1:
    Luôn tìm Connect trực tiếp trên
    profile header trước.

    Có thể là:
    - <button>Connect</button>
    - <a>Connect</a>

    Không lấy Connect từ sidebar.
    """

    _check_deadline(
        deadline
    )

    selectors = (
        "button:has-text('Connect')",
        "a:has-text('Connect')",
        "button[aria-label*='Connect']",
        "button[aria-label*='connect']",
        "a[aria-label*='Connect']",
        "a[aria-label*='connect']",
    )

    viewport = page.viewport_size

    if viewport:
        max_x = (
            viewport["width"]
            * 0.72
        )
    else:
        max_x = 950

    valid_candidates = []

    for selector in selectors:
        _check_deadline(
            deadline
        )

        try:
            candidates = page.locator(
                selector
            )

            count = candidates.count()

            for index in range(count):
                _check_deadline(
                    deadline
                )

                candidate = candidates.nth(
                    index
                )

                try:
                    timeout = _remaining_ms(
                        deadline,
                        maximum_ms=250,
                    )

                    if not candidate.is_visible(
                        timeout=timeout
                    ):
                        continue

                    text = (
                        candidate
                        .inner_text()
                        .strip()
                    )

                    # Chỉ nhận đúng action Connect.
                    # Tránh những element chứa text dài.
                    if text.lower() != "connect":
                        continue

                    box = (
                        candidate
                        .bounding_box()
                    )

                    if not box:
                        continue

                    x = box["x"]
                    y = box["y"]

                    print(
                        "DIRECT CONNECT candidate:",
                        candidate.evaluate(
                            "(el) => el.tagName"
                        ),
                        "text=",
                        text,
                        "x=",
                        x,
                        "y=",
                        y,
                    )

                    # Không lấy Connect quá sâu
                    # bên dưới profile.
                    if y > 650:
                        continue

                    # Không lấy sidebar bên phải.
                    if x > max_x:
                        continue

                    valid_candidates.append(
                        (
                            y,
                            x,
                            candidate,
                        )
                    )

                except LinkedInProfileActionTimeout:
                    raise

                except Exception:
                    continue

        except LinkedInProfileActionTimeout:
            raise

        except Exception:
            continue

    if not valid_candidates:
        print(
            "No direct Connect "
            "in profile header."
        )

        return False

    # Nút nằm cao nhất trong profile header
    # được ưu tiên.
    valid_candidates.sort(
        key=lambda item: (
            item[0],
            item[1],
        )
    )

    y, x, connect = (
        valid_candidates[0]
    )

    print(
        "DIRECT CONNECT selected:",
        "x=",
        x,
        "y=",
        y,
    )

    try:
        # DOM click tránh trường hợp
        # nav overlay intercept pointer.
        connect.evaluate(
            "(element) => element.click()"
        )

        print(
            "Direct Connect clicked."
        )

        return True

    except Exception as exc:
        print(
            "DIRECT CONNECT CLICK ERROR:",
            f"{type(exc).__name__}: {exc}",
        )

        return False

# =========================================================
# MORE BUTTON
# =========================================================


def _click_more_button(
    page: Page,
    *,
    deadline: float,
) -> bool:
    """
    Click nút More trong profile header.

    Hỗ trợ các case:
    - dấu ... có aria-label="More"
    - aria-label chứa "More"
    - button có text "More"
    - button title="More"

    Chỉ lấy button nằm trong vùng header,
    tránh More ở sidebar hoặc section khác.
    """

    _check_deadline(
        deadline
    )

    selectors = (
        "button[aria-label='More']",
        "button[aria-label*='More']",
        "button[aria-label*='more']",
        "button[title='More']",
        "button:has-text('More')",
    )

    viewport = page.viewport_size

    if viewport:
        max_x = (
            viewport["width"]
            * 0.78
        )
    else:
        max_x = 1050

    candidates_found = []

    try:
        for selector in selectors:
            _check_deadline(
                deadline
            )

            candidates = (
                page.locator(
                    selector
                )
            )

            count = (
                candidates.count()
            )

            for index in range(
                count
            ):
                _check_deadline(
                    deadline
                )

                button = (
                    candidates
                    .nth(index)
                )

                try:
                    timeout = _remaining_ms(
                        deadline,
                        maximum_ms=250,
                    )

                    if not button.is_visible(
                        timeout=timeout
                    ):
                        continue

                    box = (
                        button
                        .bounding_box()
                    )

                    if not box:
                        continue

                    x = box["x"]
                    y = box["y"]

                    # Chỉ vùng profile header
                    if y > 650:
                        continue

                    # Tránh sidebar phải
                    if x > max_x:
                        continue

                    text = ""

                    try:
                        text = (
                            button
                            .inner_text()
                            .strip()
                        )
                    except Exception:
                        pass

                    aria_label = (
                        button.get_attribute(
                            "aria-label"
                        )
                        or ""
                    )

                    title = (
                        button.get_attribute(
                            "title"
                        )
                        or ""
                    )

                    print(
                        "MORE candidate:",
                        "selector=",
                        selector,
                        "text=",
                        text,
                        "aria=",
                        aria_label,
                        "title=",
                        title,
                        "x=",
                        x,
                        "y=",
                        y,
                    )

                    candidates_found.append(
                        (
                            y,
                            x,
                            button,
                        )
                    )

                except LinkedInProfileActionTimeout:
                    raise

                except Exception:
                    continue

        if not candidates_found:
            print(
                "No header More button found."
            )

            return False

        # Ưu tiên button nằm cao nhất,
        # rồi bên trái hơn.
        candidates_found.sort(
            key=lambda item: (
                item[0],
                item[1],
            )
        )

        y, x, button = (
            candidates_found[0]
        )

        print(
            "MORE selected:",
            "x=",
            x,
            "y=",
            y,
        )

        before = (
            button.get_attribute(
                "aria-expanded"
            )
        )

        print(
            "MORE before:",
            before,
        )

        # DOM click tránh overlay.
        button.evaluate(
            "(element) => element.click()"
        )

        timeout = _remaining_ms(
            deadline,
            maximum_ms=400,
        )

        page.wait_for_timeout(
            min(
                timeout,
                400,
            )
        )

        after = (
            button.get_attribute(
                "aria-expanded"
            )
        )

        print(
            "MORE after:",
            after,
        )

        # Một số version LinkedIn không đổi
        # aria-expanded nhưng menu vẫn mở.
        if (
            after == "true"
            or before != after
        ):
            return True

        # Fallback: check xem Connect
        # đã xuất hiện trong menu chưa.
        menu_connect_selectors = (
            "a[href*='/preload/custom-invite/']",
            "[role='menuitem']:has-text('Connect')",
            "li:has-text('Connect')",
        )

        for selector in menu_connect_selectors:
            if _is_visible(
                page,
                selector,
                deadline=deadline,
                maximum_ms=250,
            ):
                print(
                    "More menu detected "
                    "via Connect item."
                )

                return True

        return False

    except LinkedInProfileActionTimeout:
        raise

    except Exception as exc:
        print(
            "MORE BUTTON ERROR:",
            f"{type(exc).__name__}: {exc}",
        )

        return False


# =========================================================
# CONNECT IN MORE MENU
# =========================================================


def _click_connect_in_more_menu(
    page: Page,
    *,
    deadline: float,
) -> bool:
    strong_selectors = (
        (
            "a[href*="
            "'/preload/custom-invite/']"
        ),
        (
            "a[href*="
            "'preload/custom-invite']"
        ),
    )

    if _click_first_visible(
        page,
        strong_selectors,
        deadline=deadline,
        maximum_ms=700,
    ):
        print(
            "Connect clicked using "
            "invite href."
        )

        return True

    fallback_selectors = (
        (
            "[role='menuitem']"
            ":has-text('Connect')"
        ),
        "a:has-text('Connect')",
        "li:has-text('Connect')",
        "span:has-text('Connect')",
    )

    if _click_first_visible(
        page,
        fallback_selectors,
        deadline=deadline,
        maximum_ms=500,
    ):
        print(
            "Connect clicked using "
            "text fallback."
        )

        return True

    return False


# =========================================================
# CONNECT DISCOVERY
# =========================================================


def _click_connect(
    page: Page,
    *,
    deadline: float,
) -> bool:
    print("")
    print(
        "Checking direct Connect..."
    )

    if _click_direct_connect(
        page,
        deadline=deadline,
    ):
        print(
            "Direct Connect found "
            "and clicked."
        )

        return True

    print(
        "Direct Connect not found."
    )

    _check_deadline(
        deadline
    )

    print(
        "Opening More menu..."
    )

    if not _click_more_button(
        page,
        deadline=deadline,
    ):
        print(
            "Could not open More menu."
        )

        return False

    print(
        "More menu opened."
    )

    print(
        "Looking for Connect "
        "inside More menu..."
    )

    if _click_connect_in_more_menu(
        page,
        deadline=deadline,
    ):
        print(
            "Connect found in "
            "More menu."
        )

        return True

    print(
        "Connect not found in "
        "More menu."
    )

    return False


# =========================================================
# SEND WITHOUT NOTE
# =========================================================


def _click_send_without_note(
    page: Page,
    *,
    deadline: float,
) -> bool:
    selectors = (
        (
            "button:has-text("
            "'Send without a note'"
            ")"
        ),
        (
            "button:has-text("
            "'Send without note'"
            ")"
        ),
        (
            "button[aria-label*="
            "'Send without']"
        ),
    )

    return _click_first_visible(
        page,
        selectors,
        deadline=deadline,
        maximum_ms=650,
    )


# =========================================================
# MAIN
# =========================================================


def connect_profile(
    *,
    browser: LinkedInBrowserManager,
    linkedin_url: str,
) -> LinkedInConnectResult:
    cleaned_url = str(
        linkedin_url
        or ""
    ).strip()

    if not cleaned_url:
        return LinkedInConnectResult(
            linkedin_url="",
            final_url="",
            status="failed",
            message=(
                "invalid_url: LinkedIn URL "
                "cannot be empty."
            ),
        )

    deadline = (
        _build_deadline()
    )

    page: Page | None = None

    try:
        print("")
        print("=" * 60)
        print("LINKEDIN CONNECT")
        print("=" * 60)

        print(
            f"URL: {cleaned_url}"
        )

        # -------------------------------------------------
        # OPEN PROFILE
        # -------------------------------------------------

        remaining = _remaining_ms(
            deadline,
            maximum_ms=PROFILE_TIMEOUT_MS,
        )

        page = (
            browser
            .open_linkedin_url(
                cleaned_url,
                overall_timeout_ms=remaining,
                raise_on_navigation_timeout=True,
            )
        )

        _check_deadline(
            deadline
        )

        # -------------------------------------------------
        # 404 / NOT FOUND
        # -------------------------------------------------

        if _is_profile_not_found(
            page,
            deadline=deadline,
        ):
            print(
                "Result: profile not found."
            )

            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="failed",
                message=(
                    "url_not_found: "
                    "LinkedIn profile does "
                    "not exist or returned 404."
                ),
            )

        # -------------------------------------------------
        # ALREADY PENDING
        # -------------------------------------------------

        if _has_pending_state(
            page,
            deadline=deadline,
        ):
            print(
                "Result: already pending."
            )

            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="pending",
                message=(
                    "Connection invitation "
                    "was already sent."
                ),
            )

        # -------------------------------------------------
        # CONNECT
        # -------------------------------------------------

        connect_clicked = (
            _click_connect(
                page,
                deadline=deadline,
            )
        )

        if not connect_clicked:
            # ---------------------------------------------
            # ALREADY CONNECTED
            # ---------------------------------------------

            if _has_first_degree_state(
                page,
                deadline=deadline,
            ):
                print(
                    "Result: already connected."
                )

                return LinkedInConnectResult(
                    linkedin_url=cleaned_url,
                    final_url=page.url,
                    status="already_connected",
                    message=(
                        "Profile is already "
                        "a 1st-degree connection."
                    ),
                )

            # ---------------------------------------------
            # CONNECT UNAVAILABLE
            # ---------------------------------------------

            print(
                "Result: Connect unavailable."
            )

            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="connect_unavailable",
                message=(
                    "connect_unavailable: "
                    "Connect action was not found."
                ),
            )

        # -------------------------------------------------
        # CONNECT CLICKED
        # -------------------------------------------------

        _check_deadline(
            deadline
        )

        remaining = _remaining_ms(
            deadline,
            maximum_ms=450,
        )

        page.wait_for_timeout(
            min(
                remaining,
                450,
            )
        )

        # -------------------------------------------------
        # PENDING DIRECTLY AFTER CLICK
        # -------------------------------------------------

        if _has_pending_state(
            page,
            deadline=deadline,
        ):
            print(
                "Result: invitation sent."
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
            page,
            deadline=deadline,
        ):
            print(
                "Send without note clicked."
            )

            _check_deadline(
                deadline
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
        # FINAL PENDING CHECK
        # -------------------------------------------------

        if _has_pending_state(
            page,
            deadline=deadline,
        ):
            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="invitation_sent",
                message=(
                    "Connection invitation sent."
                ),
            )

        # -------------------------------------------------
        # UNKNOWN ACTION RESULT
        # -------------------------------------------------

        return LinkedInConnectResult(
            linkedin_url=cleaned_url,
            final_url=page.url,
            status="failed",
            message=(
                "action_error: Connect was "
                "clicked but final state "
                "could not be confirmed."
            ),
        )

    # =====================================================
    # PROFILE TIMEOUT
    # =====================================================

    except (
        LinkedInProfileActionTimeout,
        LinkedInBrowserTimeoutError,
        PlaywrightTimeoutError,
    ) as exc:
        final_url = (
            page.url
            if page is not None
            else ""
        )

        print(
            "Result: PROFILE TIMEOUT"
        )

        return LinkedInConnectResult(
            linkedin_url=cleaned_url,
            final_url=final_url,
            status="failed",
            message=(
                "timeout: profile exceeded "
                "the 10 second processing limit. "
                f"{exc}"
            ),
        )

    # =====================================================
    # SESSION ERROR
    # =====================================================

    except LinkedInSessionError as exc:
        final_url = (
            page.url
            if page is not None
            else ""
        )

        return LinkedInConnectResult(
            linkedin_url=cleaned_url,
            final_url=final_url,
            status="failed",
            message=(
                "session_error: "
                f"{exc}"
            ),
        )

    # =====================================================
    # OTHER ERROR
    # =====================================================

    except Exception as exc:
        final_url = (
            page.url
            if page is not None
            else ""
        )

        return LinkedInConnectResult(
            linkedin_url=cleaned_url,
            final_url=final_url,
            status="failed",
            message=(
                "action_error: "
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )
