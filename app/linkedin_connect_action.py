from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

from playwright.sync_api import (
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from app.linkedin_browser import (
    LinkedInBrowserManager,
    LinkedInBrowserTimeoutError,
    LinkedInSessionError,
)


PROFILE_TIMEOUT_MS = 10_000
MORE_MAX_ATTEMPTS = 2
MORE_VERIFY_WINDOW_MS = 900
FINAL_STATE_VERIFY_WINDOW_MS = 1_500
FINAL_STATE_POLL_MS = 180

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


class LinkedInProfileActionTimeout(RuntimeError):
    pass


def _build_deadline() -> float:
    return time.monotonic() + (PROFILE_TIMEOUT_MS / 1000)


def _remaining_ms(deadline: float, *, maximum_ms: int) -> int:
    remaining = int((deadline - time.monotonic()) * 1000)
    if remaining <= 0:
        raise LinkedInProfileActionTimeout(
            "Profile processing exceeded the 10 second limit."
        )
    return max(1, min(remaining, maximum_ms))


def _check_deadline(deadline: float) -> None:
    if time.monotonic() >= deadline:
        raise LinkedInProfileActionTimeout(
            "Profile processing exceeded the 10 second limit."
        )


def _sleep(page: Page, *, deadline: float, milliseconds: int) -> None:
    timeout = _remaining_ms(deadline, maximum_ms=milliseconds)
    page.wait_for_timeout(min(timeout, milliseconds))


def _is_visible_locator(
    locator: Locator,
    *,
    deadline: float,
    maximum_ms: int = 250,
) -> bool:
    _check_deadline(deadline)
    try:
        return locator.is_visible(
            timeout=_remaining_ms(deadline, maximum_ms=maximum_ms)
        )
    except LinkedInProfileActionTimeout:
        raise
    except Exception:
        return False


def _is_visible(
    page: Page,
    selector: str,
    *,
    deadline: float,
    maximum_ms: int = 250,
) -> bool:
    try:
        return _is_visible_locator(
            page.locator(selector).first,
            deadline=deadline,
            maximum_ms=maximum_ms,
        )
    except LinkedInProfileActionTimeout:
        raise
    except Exception:
        return False


def _click_dom(locator: Locator) -> bool:
    try:
        locator.evaluate(
            """
            (element) => {
                element.scrollIntoView({block: 'center', inline: 'center'});
                element.click();
            }
            """
        )
        return True
    except Exception:
        return False


def _click_locator(
    locator: Locator,
    *,
    deadline: float,
    maximum_ms: int = 400,
) -> bool:
    if _click_dom(locator):
        return True
    try:
        locator.click(
            timeout=_remaining_ms(deadline, maximum_ms=maximum_ms)
        )
        return True
    except Exception:
        return False


def _click_first_visible(
    page: Page,
    selectors: tuple[str, ...],
    *,
    deadline: float,
    maximum_ms: int = 450,
) -> bool:
    for selector in selectors:
        _check_deadline(deadline)
        try:
            candidates = page.locator(selector)
            for index in range(candidates.count()):
                candidate = candidates.nth(index)
                if not _is_visible_locator(
                    candidate,
                    deadline=deadline,
                    maximum_ms=180,
                ):
                    continue
                if _click_locator(
                    candidate,
                    deadline=deadline,
                    maximum_ms=maximum_ms,
                ):
                    return True
        except LinkedInProfileActionTimeout:
            raise
        except Exception:
            continue
    return False


def _is_profile_not_found(page: Page, *, deadline: float) -> bool:
    current_url = (page.url or "").lower()
    if "/404" in current_url or "/error" in current_url:
        return True

    try:
        body_text = (
            page.locator("body")
            .inner_text(
                timeout=_remaining_ms(deadline, maximum_ms=600)
            )
            .lower()
        )
    except LinkedInProfileActionTimeout:
        raise
    except Exception:
        return False

    signals = (
        "this page doesn’t exist",
        "this page doesn't exist",
        "page not found",
        "profile not found",
        "this profile is not available",
        "the profile you requested does not exist",
    )
    return any(signal in body_text for signal in signals)


def _has_pending_state(page: Page, *, deadline: float) -> bool:
    selectors = (
        "button:has-text('Pending')",
        "button[aria-label*='Pending']",
        "[role='button'][aria-label*='Pending']",
        "span:has-text('Pending')",
    )
    return any(
        _is_visible(
            page,
            selector,
            deadline=deadline,
            maximum_ms=180,
        )
        for selector in selectors
    )


def _has_first_degree_state(page: Page, *, deadline: float) -> bool:
    try:
        candidates = page.get_by_text("1st", exact=True)
        for index in range(candidates.count()):
            candidate = candidates.nth(index)
            if not _is_visible_locator(
                candidate,
                deadline=deadline,
                maximum_ms=180,
            ):
                continue
            box = candidate.bounding_box()
            if box and box["y"] <= 550:
                return True
    except LinkedInProfileActionTimeout:
        raise
    except Exception:
        pass
    return False


def _has_invite_modal(page: Page, *, deadline: float) -> bool:
    selectors = (
        "[role='dialog'] button:has-text('Send without a note')",
        "[role='dialog'] button:has-text('Send without note')",
        "button:has-text('Send without a note')",
        "button:has-text('Send without note')",
    )
    return any(
        _is_visible(
            page,
            selector,
            deadline=deadline,
            maximum_ms=160,
        )
        for selector in selectors
    )


def _get_profile_vanity_name(
    page: Page,
) -> str:
    """
    Lấy vanity name trực tiếp từ URL profile hiện tại.

    Ví dụ:
        https://www.linkedin.com/in/austinsena/
    ->
        austinsena
    """
    try:
        parsed = urlsplit(
            page.url
            or ""
        )

        path = (
            parsed.path
            .strip()
            .rstrip("/")
        )

        if not path.startswith(
            "/in/"
        ):
            return ""

        vanity_name = (
            path[4:]
            .strip("/")
            .strip()
        )

        return vanity_name

    except Exception:
        return ""


# =========================================================
# PATH 1: DIRECT CONNECT
# =========================================================

def _click_direct_connect(page: Page, *, deadline: float) -> bool:
    selectors = (
        "button:has-text('Connect')",
        "a:has-text('Connect')",
        "button[aria-label*='Connect']",
        "button[aria-label*='connect']",
        "a[aria-label*='Connect']",
        "a[aria-label*='connect']",
    )

    viewport = page.viewport_size
    max_x = viewport["width"] * 0.72 if viewport else 950
    valid = []
    seen = set()

    for selector in selectors:
        _check_deadline(deadline)
        try:
            candidates = page.locator(selector)
            for index in range(candidates.count()):
                candidate = candidates.nth(index)
                if not _is_visible_locator(
                    candidate,
                    deadline=deadline,
                    maximum_ms=160,
                ):
                    continue

                try:
                    text = candidate.inner_text().strip().lower()
                except Exception:
                    text = ""

                if text != "connect":
                    continue

                box = candidate.bounding_box()
                if not box:
                    continue

                x = box["x"]
                y = box["y"]
                if y > 650 or x > max_x:
                    continue

                key = (round(x), round(y))
                if key in seen:
                    continue
                seen.add(key)
                valid.append((y, x, candidate))
        except LinkedInProfileActionTimeout:
            raise
        except Exception:
            continue

    if not valid:
        print("PATH 1: no direct Connect in profile header")
        return False

    valid.sort(key=lambda item: (item[0], item[1]))
    y, x, connect = valid[0]
    print("PATH 1: direct Connect selected", x, y)

    if _click_locator(connect, deadline=deadline):
        print("PATH 1: direct Connect clicked")
        return True

    return False


# =========================================================
# MORE MENU
# =========================================================

def _collect_more_buttons(
    page: Page,
    *,
    deadline: float,
) -> list[tuple[float, float, Locator]]:
    locators: list[Locator] = []

    try:
        texts = page.get_by_text("More", exact=True)
        for index in range(texts.count()):
            text_node = texts.nth(index)
            if not _is_visible_locator(
                text_node,
                deadline=deadline,
                maximum_ms=160,
            ):
                continue
            button = text_node.locator("xpath=ancestor::button[1]")
            if button.count() > 0:
                locators.append(button.first)
    except LinkedInProfileActionTimeout:
        raise
    except Exception:
        pass

    selectors = (
        "button[aria-label='More']",
        "button[aria-label*='More actions']",
        "button[title='More']",
        "button:has-text('More')",
    )

    for selector in selectors:
        try:
            candidates = page.locator(selector)
            for index in range(candidates.count()):
                locators.append(candidates.nth(index))
        except Exception:
            continue

    valid = []
    seen = set()

    for button in locators:
        _check_deadline(deadline)
        try:
            if not _is_visible_locator(
                button,
                deadline=deadline,
                maximum_ms=150,
            ):
                continue

            box = button.bounding_box()
            if not box:
                continue

            x = box["x"]
            y = box["y"]
            if y > 650:
                continue

            try:
                text = button.inner_text().strip().lower()
            except Exception:
                text = ""

            try:
                aria = (button.get_attribute("aria-label") or "").strip().lower()
            except Exception:
                aria = ""

            try:
                title = (button.get_attribute("title") or "").strip().lower()
            except Exception:
                title = ""

            if not (
                text == "more"
                or aria == "more"
                or "more actions" in aria
                or title == "more"
            ):
                continue

            key = (round(x), round(y))
            if key in seen:
                continue
            seen.add(key)
            valid.append((y, x, button))
        except LinkedInProfileActionTimeout:
            raise
        except Exception:
            continue

    valid.sort(key=lambda item: (item[0], item[1]))
    return valid


def _visible_exact_connect_exists(
    page: Page,
    *,
    deadline: float,
) -> bool:
    """
    Sau khi More được click, LinkedIn không phải lúc nào cũng
    gắn role='menu' / role='menuitem' hoặc aria-expanded.

    Vì PATH 1 direct Connect đã được check trước đó,
    một exact-text Connect mới xuất hiện sau click More
    là signal đủ mạnh để coi menu/action sheet đã mở.
    """
    try:
        texts = page.get_by_text(
            "Connect",
            exact=True,
        )

        for index in range(texts.count()):
            node = texts.nth(index)

            if not _is_visible_locator(
                node,
                deadline=deadline,
                maximum_ms=100,
            ):
                continue

            box = node.bounding_box()

            if not box:
                continue

            # Tránh các Connect nằm quá sâu dưới profile.
            if box["y"] > 900:
                continue

            return True

    except LinkedInProfileActionTimeout:
        raise

    except Exception:
        pass

    return False


def _more_menu_is_open(
    page: Page,
    *,
    button: Locator | None,
    deadline: float,
) -> bool:
    """
    Verify More theo nhiều signal.

    Không bắt buộc LinkedIn phải có role menu/menuitem vì DOM
    của More thay đổi giữa các profile/layout.
    """
    if button is not None:
        try:
            expanded = (
                button
                .get_attribute("aria-expanded")
                or ""
            ).strip().lower()

            if expanded == "true":
                return True

        except Exception:
            pass

    # Strong signal: custom invite action đã render.
    try:
        invite_links = page.locator(
            "a[href*='custom-invite']"
        )

        for index in range(invite_links.count()):
            if _is_visible_locator(
                invite_links.nth(index),
                deadline=deadline,
                maximum_ms=100,
            ):
                return True

    except LinkedInProfileActionTimeout:
        raise

    except Exception:
        pass

    # Important fallback:
    # exact visible Connect itself is enough after More click.
    if _visible_exact_connect_exists(
        page,
        deadline=deadline,
    ):
        return True

    return False


def _wait_for_more_menu(
    page: Page,
    *,
    button: Locator | None,
    deadline: float,
) -> bool:
    verify_deadline = min(
        deadline,
        time.monotonic()
        + (MORE_VERIFY_WINDOW_MS / 1000),
    )

    while time.monotonic() < verify_deadline:
        if _more_menu_is_open(
            page,
            button=button,
            deadline=deadline,
        ):
            return True

        _sleep(
            page,
            deadline=deadline,
            milliseconds=80,
        )

    return False


def _click_more_button(
    page: Page,
    *,
    deadline: float,
) -> bool:
    """
    Open đúng More button trong profile header.

    DOM thật đã xác nhận có thể có nhiều text "More" trên page.
    Hai nhóm thường gặp:
    - top/navigation More ở y rất nhỏ
    - profile-header More ở khoảng giữa page

    Chỉ nhận button trong vùng profile header:
        150 <= y <= 650

    Đồng thời dedupe nhiều span cùng trỏ về một button.
    """
    _check_deadline(deadline)

    for attempt in range(
        1,
        MORE_MAX_ATTEMPTS + 1,
    ):
        print(
            f"MORE attempt {attempt}/{MORE_MAX_ATTEMPTS}"
        )

        try:
            more_texts = page.get_by_text(
                "More",
                exact=True,
            )

            candidates = []
            seen_buttons = set()

            for index in range(
                more_texts.count()
            ):
                _check_deadline(deadline)

                text_node = more_texts.nth(
                    index
                )

                if not _is_visible_locator(
                    text_node,
                    deadline=deadline,
                    maximum_ms=180,
                ):
                    continue

                button = text_node.locator(
                    "xpath=ancestor::button[1]"
                )

                if button.count() == 0:
                    continue

                button = button.first

                if not _is_visible_locator(
                    button,
                    deadline=deadline,
                    maximum_ms=180,
                ):
                    continue

                box = button.bounding_box()

                if not box:
                    continue

                x = box["x"]
                y = box["y"]

                # IMPORTANT:
                # bỏ More ở top navigation,
                # chỉ nhận vùng profile header.
                if y < 150:
                    continue

                if y > 650:
                    continue

                # Dedupe nhiều span cùng trỏ về cùng button.
                key = (
                    round(x),
                    round(y),
                    round(box.get("width", 0)),
                    round(box.get("height", 0)),
                )

                if key in seen_buttons:
                    continue

                seen_buttons.add(
                    key
                )

                try:
                    aria_expanded = (
                        button
                        .get_attribute("aria-expanded")
                    )
                except Exception:
                    aria_expanded = None

                candidates.append(
                    (
                        y,
                        x,
                        aria_expanded,
                        button,
                    )
                )

            if not candidates:
                print(
                    "MORE: no profile-header More button found"
                )
                return False

            # Trong vùng profile header, ưu tiên button thấp nhất một chút
            # để tránh action khác ở gần top nếu LinkedIn có nhiều More.
            candidates.sort(
                key=lambda item: (
                    -item[0],
                    item[1],
                )
            )

            y, x, aria_expanded, button = (
                candidates[0]
            )

            print(
                "MORE selected:",
                "x=",
                x,
                "y=",
                y,
                "aria-expanded=",
                aria_expanded,
            )

            current_expanded = (
                str(
                    aria_expanded
                    or ""
                )
                .strip()
                .lower()
            )

            if current_expanded == "true":
                print(
                    "MORE already open"
                )
                return True

            if not _click_locator(
                button,
                deadline=deadline,
                maximum_ms=420,
            ):
                print(
                    "MORE click failed"
                )
            else:
                verify_deadline = min(
                    deadline,
                    time.monotonic()
                    + (
                        MORE_VERIFY_WINDOW_MS
                        / 1000
                    ),
                )

                vanity_name = (
                    _get_profile_vanity_name(
                        page
                    )
                )

                while (
                    time.monotonic()
                    < verify_deadline
                ):
                    _check_deadline(
                        deadline
                    )

                    try:
                        expanded = (
                            button
                            .get_attribute(
                                "aria-expanded"
                            )
                            or ""
                        ).strip().lower()
                    except Exception:
                        expanded = ""

                    if expanded == "true":
                        print(
                            "MORE verified open via aria-expanded=true"
                        )
                        return True

                    # Strong fallback:
                    # đúng custom-invite của profile hiện tại xuất hiện.
                    if vanity_name:
                        try:
                            exact_link = page.locator(
                                (
                                    "a[href*='/preload/custom-invite/']"
                                    f"[href*='vanityName={vanity_name}']"
                                )
                            )

                            for link_index in range(
                                exact_link.count()
                            ):
                                link = exact_link.nth(
                                    link_index
                                )

                                if _is_visible_locator(
                                    link,
                                    deadline=deadline,
                                    maximum_ms=100,
                                ):
                                    print(
                                        "MORE verified open via exact profile custom-invite"
                                    )
                                    return True

                        except LinkedInProfileActionTimeout:
                            raise

                        except Exception:
                            pass

                    _sleep(
                        page,
                        deadline=deadline,
                        milliseconds=80,
                    )

        except LinkedInProfileActionTimeout:
            raise

        except Exception as exc:
            print(
                "MORE error:",
                (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            )

        if attempt < MORE_MAX_ATTEMPTS:
            _sleep(
                page,
                deadline=deadline,
                milliseconds=120,
            )

    return False


# =========================================================
# PATH 2: MORE -> custom-invite
# =========================================================

def _click_connect_via_custom_invite(
    page: Page,
    *,
    deadline: float,
) -> bool:
    """
    PATH 2 - strongest More-menu path.

    Quan trọng:
    LinkedIn page có thể có nhiều custom-invite links
    ở sidebar / recommendation.

    Vì vậy phải match đúng vanityName của profile hiện tại.

    Ví dụ profile:
        /in/austinsena/

    chỉ click:
        /preload/custom-invite/?vanityName=austinsena
    """
    _check_deadline(deadline)

    vanity_name = (
        _get_profile_vanity_name(
            page
        )
    )

    if not vanity_name:
        print(
            "PATH 2: could not derive current profile vanityName"
        )
        return False

    selectors = (
        (
            "a[href*='/preload/custom-invite/']"
            f"[href*='vanityName={vanity_name}']"
        ),
        (
            "a[href*='custom-invite']"
            f"[href*='vanityName={vanity_name}']"
        ),
    )

    for selector in selectors:
        _check_deadline(deadline)

        try:
            links = page.locator(
                selector
            )

            for index in range(
                links.count()
            ):
                _check_deadline(deadline)

                link = links.nth(
                    index
                )

                if not _is_visible_locator(
                    link,
                    deadline=deadline,
                    maximum_ms=180,
                ):
                    continue

                try:
                    href = (
                        link
                        .get_attribute("href")
                        or ""
                    )
                except Exception:
                    href = ""

                try:
                    text_value = (
                        link
                        .inner_text()
                        .strip()
                    )
                except Exception:
                    text_value = ""

                try:
                    role = (
                        link
                        .get_attribute("role")
                        or ""
                    )
                except Exception:
                    role = ""

                print(
                    "PATH 2 exact candidate:",
                    "href=",
                    href,
                    "role=",
                    role,
                    "text=",
                    repr(text_value),
                )

                if (
                    "custom-invite"
                    not in href
                ):
                    continue

                if (
                    f"vanityName={vanity_name}"
                    not in href
                ):
                    continue

                if _click_locator(
                    link,
                    deadline=deadline,
                    maximum_ms=420,
                ):
                    print(
                        "PATH 2: clicked exact profile custom-invite"
                    )
                    return True

        except LinkedInProfileActionTimeout:
            raise

        except Exception as exc:
            print(
                "PATH 2 error:",
                (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            )

    return False


# =========================================================
# PATH 3: MORE -> exact text Connect
# =========================================================

def _click_connect_via_menu_text(
    page: Page,
    *,
    deadline: float,
) -> bool:
    """
    PATH 3 fallback:
    exact text Connect trong vùng menu vừa mở.

    Ưu tiên clickable <a> có vanityName đúng profile hiện tại.
    Chỉ khi không có href mới fallback a/button text.
    """
    _check_deadline(deadline)

    vanity_name = (
        _get_profile_vanity_name(
            page
        )
    )

    try:
        texts = page.get_by_text(
            "Connect",
            exact=True,
        )

        for index in range(
            texts.count()
        ):
            _check_deadline(deadline)

            node = texts.nth(
                index
            )

            if not _is_visible_locator(
                node,
                deadline=deadline,
                maximum_ms=180,
            ):
                continue

            box = node.bounding_box()

            if not box:
                continue

            # Menu của profile nằm gần header;
            # loại recommendation Connect sâu phía dưới.
            if box["y"] < 120:
                continue

            if box["y"] > 900:
                continue

            clickable = node.locator(
                "xpath=ancestor-or-self::*["
                "self::a or self::button"
                "][1]"
            )

            if clickable.count() == 0:
                continue

            clickable = (
                clickable.first
            )

            if not _is_visible_locator(
                clickable,
                deadline=deadline,
                maximum_ms=150,
            ):
                continue

            try:
                href = (
                    clickable
                    .get_attribute("href")
                    or ""
                )
            except Exception:
                href = ""

            try:
                role = (
                    clickable
                    .get_attribute("role")
                    or ""
                )
            except Exception:
                role = ""

            # Nếu có href custom-invite,
            # bắt buộc đúng vanityName hiện tại.
            if (
                "custom-invite"
                in href
            ):
                if (
                    not vanity_name
                    or (
                        f"vanityName={vanity_name}"
                        not in href
                    )
                ):
                    continue

            print(
                "PATH 3 candidate:",
                "x=",
                box["x"],
                "y=",
                box["y"],
                "href=",
                href,
                "role=",
                role,
            )

            if _click_locator(
                clickable,
                deadline=deadline,
                maximum_ms=420,
            ):
                print(
                    "PATH 3: clicked profile-scoped Connect"
                )
                return True

    except LinkedInProfileActionTimeout:
        raise

    except Exception as exc:
        print(
            "PATH 3 error:",
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )

    return False


def _click_connect_once(page: Page, *, deadline: float) -> bool:
    print("Checking PATH 1: direct Connect")
    if _click_direct_connect(page, deadline=deadline):
        return True

    print("Opening More for PATH 2/3")
    if not _click_more_button(page, deadline=deadline):
        return False

    print("Checking PATH 2: custom-invite")
    if _click_connect_via_custom_invite(page, deadline=deadline):
        return True

    print("Checking PATH 3: exact Connect text")
    if _click_connect_via_menu_text(page, deadline=deadline):
        return True

    return False


def _click_connect(page: Page, *, deadline: float) -> bool:
    if _click_connect_once(page, deadline=deadline):
        return True

    # One short second discovery round when enough time remains.
    if (deadline - time.monotonic()) < 1.4:
        return False

    print("Connect discovery retry")
    _sleep(page, deadline=deadline, milliseconds=180)
    return _click_connect_once(page, deadline=deadline)


# =========================================================
# SEND WITHOUT NOTE
# =========================================================

def _click_send_without_note(page: Page, *, deadline: float) -> bool:
    selectors = (
        "button:has-text('Send without a note')",
        "button:has-text('Send without note')",
        "button[aria-label*='Send without']",
    )
    return _click_first_visible(
        page,
        selectors,
        deadline=deadline,
        maximum_ms=420,
    )


# =========================================================
# FINAL STATE CONFIRMATION
# =========================================================

def _confirm_after_connect_click(
    page: Page,
    *,
    deadline: float,
) -> ConnectStatus | None:
    verify_deadline = min(
        deadline,
        time.monotonic() + (FINAL_STATE_VERIFY_WINDOW_MS / 1000),
    )

    send_attempted = False

    while time.monotonic() < verify_deadline:
        _check_deadline(deadline)

        if _has_pending_state(page, deadline=deadline):
            return "invitation_sent"

        if _has_first_degree_state(page, deadline=deadline):
            return "already_connected"

        if (
            not send_attempted
            and _has_invite_modal(page, deadline=deadline)
        ):
            print("Invite modal detected")
            if _click_send_without_note(page, deadline=deadline):
                print("Send without note clicked")
                send_attempted = True
                _sleep(page, deadline=deadline, milliseconds=180)
                continue
            send_attempted = True

        _sleep(
            page,
            deadline=deadline,
            milliseconds=FINAL_STATE_POLL_MS,
        )

    if _has_pending_state(page, deadline=deadline):
        return "invitation_sent"

    if _has_first_degree_state(page, deadline=deadline):
        return "already_connected"

    return None


# =========================================================
# MAIN
# =========================================================

def connect_profile(
    *,
    browser: LinkedInBrowserManager,
    linkedin_url: str,
) -> LinkedInConnectResult:
    cleaned_url = str(linkedin_url or "").strip()

    if not cleaned_url:
        return LinkedInConnectResult(
            linkedin_url="",
            final_url="",
            status="failed",
            message="invalid_url: LinkedIn URL cannot be empty.",
        )

    deadline = _build_deadline()
    page: Page | None = None

    try:
        print("")
        print("=" * 60)
        print("LINKEDIN CONNECT")
        print("=" * 60)
        print(f"URL: {cleaned_url}")

        page = browser.open_linkedin_url(
            cleaned_url,
            overall_timeout_ms=_remaining_ms(
                deadline,
                maximum_ms=PROFILE_TIMEOUT_MS,
            ),
            raise_on_navigation_timeout=True,
        )

        _check_deadline(deadline)

        if _is_profile_not_found(page, deadline=deadline):
            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="failed",
                message=(
                    "url_not_found: LinkedIn profile does not exist or returned 404."
                ),
            )

        # Pre-action state check avoids false connect_unavailable.
        if _has_pending_state(page, deadline=deadline):
            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="pending",
                message="Connection invitation was already sent.",
            )

        if _has_first_degree_state(page, deadline=deadline):
            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="already_connected",
                message="Profile is already a 1st-degree connection.",
            )

        connect_clicked = _click_connect(page, deadline=deadline)

        if not connect_clicked:
            # Check state again before declaring unavailable.
            if _has_pending_state(page, deadline=deadline):
                return LinkedInConnectResult(
                    linkedin_url=cleaned_url,
                    final_url=page.url,
                    status="pending",
                    message="Connection invitation is pending.",
                )

            if _has_first_degree_state(page, deadline=deadline):
                return LinkedInConnectResult(
                    linkedin_url=cleaned_url,
                    final_url=page.url,
                    status="already_connected",
                    message="Profile is already a 1st-degree connection.",
                )

            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="connect_unavailable",
                message=(
                    "connect_unavailable: Connect action was not found after "
                    "direct, More/custom-invite, More/text, and retry."
                ),
            )

        confirmed = _confirm_after_connect_click(
            page,
            deadline=deadline,
        )

        if confirmed == "invitation_sent":
            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="invitation_sent",
                message="Connection invitation sent.",
            )

        if confirmed == "already_connected":
            return LinkedInConnectResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="already_connected",
                message="Profile is already a 1st-degree connection.",
            )

        # Last-chance short state check before action_error.
        if (deadline - time.monotonic()) > 0.35:
            _sleep(page, deadline=deadline, milliseconds=220)

            if _has_pending_state(page, deadline=deadline):
                return LinkedInConnectResult(
                    linkedin_url=cleaned_url,
                    final_url=page.url,
                    status="invitation_sent",
                    message="Connection invitation sent.",
                )

            if _has_first_degree_state(page, deadline=deadline):
                return LinkedInConnectResult(
                    linkedin_url=cleaned_url,
                    final_url=page.url,
                    status="already_connected",
                    message="Profile is already a 1st-degree connection.",
                )

        return LinkedInConnectResult(
            linkedin_url=cleaned_url,
            final_url=page.url,
            status="failed",
            message=(
                "action_error: Connect was clicked but final state could not "
                "be confirmed after repeated state checks."
            ),
        )

    except (
        LinkedInProfileActionTimeout,
        LinkedInBrowserTimeoutError,
        PlaywrightTimeoutError,
    ) as exc:
        return LinkedInConnectResult(
            linkedin_url=cleaned_url,
            final_url=page.url if page is not None else "",
            status="failed",
            message=(
                "timeout: profile exceeded the 10 second processing limit. "
                f"{exc}"
            ),
        )

    except LinkedInSessionError as exc:
        return LinkedInConnectResult(
            linkedin_url=cleaned_url,
            final_url=page.url if page is not None else "",
            status="failed",
            message=f"session_error: {exc}",
        )

    except Exception as exc:
        return LinkedInConnectResult(
            linkedin_url=cleaned_url,
            final_url=page.url if page is not None else "",
            status="failed",
            message=f"action_error: {type(exc).__name__}: {exc}",
        )
