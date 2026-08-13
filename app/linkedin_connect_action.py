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



def _click_ellipsis_button(
    page: Page,
    *,
    deadline: float,
) -> bool:
    """
    Restore the existing three-dot / overflow action path.

    IMPORTANT:
    - This is separate from the text "More" path.
    - No x/y/viewport logic.
    - It only targets icon/overflow buttons by semantic attributes.
    - It intentionally ignores buttons whose visible text is "More",
      so the new More logic remains isolated.

    Common LinkedIn forms covered:
    - aria-label="More actions"
    - aria-label containing "More actions"
    - aria-label="More"
    - title="More actions"
    - title="More"
    """
    _check_deadline(deadline)

    selectors = (
        "button[aria-label='More actions']",
        "button[aria-label*='More actions']",
        "button[aria-label='More']",
        "button[title='More actions']",
        "button[title='More']",
    )

    seen = set()

    for selector in selectors:
        _check_deadline(deadline)

        try:
            candidates = page.locator(selector)

            for index in range(candidates.count()):
                _check_deadline(deadline)

                button = candidates.nth(index)

                if not _is_visible_locator(
                    button,
                    deadline=deadline,
                    maximum_ms=180,
                ):
                    continue

                # Keep the text-More path completely separate.
                try:
                    visible_text = (
                        button.inner_text()
                        or ""
                    ).strip().lower()
                except Exception:
                    visible_text = ""

                if visible_text == "more":
                    continue

                # DOM identity dedupe; no coordinates.
                try:
                    key = button.evaluate(
                        """
                        (el) => {
                            if (!el.dataset.outreachEllipsisKey) {
                                el.dataset.outreachEllipsisKey =
                                    Math.random().toString(36).slice(2);
                            }
                            return el.dataset.outreachEllipsisKey;
                        }
                        """
                    )
                except Exception:
                    key = f"{selector}:{index}"

                if key in seen:
                    continue

                seen.add(key)

                try:
                    aria_label = (
                        button.get_attribute("aria-label")
                        or ""
                    )
                except Exception:
                    aria_label = ""

                try:
                    title = (
                        button.get_attribute("title")
                        or ""
                    )
                except Exception:
                    title = ""

                print(
                    "ELLIPSIS candidate:",
                    "aria-label=",
                    repr(aria_label),
                    "title=",
                    repr(title),
                )

                try:
                    expanded = (
                        button.get_attribute("aria-expanded")
                        or ""
                    ).strip().lower()
                except Exception:
                    expanded = ""

                if expanded == "true":
                    print(
                        "ELLIPSIS menu already open"
                    )
                    return True

                if not _click_locator(
                    button,
                    deadline=deadline,
                    maximum_ms=500,
                ):
                    print(
                        "ELLIPSIS candidate click failed"
                    )
                    continue

                # Do not over-gate the old working path:
                # a successful click is enough to continue to PATH 2/3.
                # Give LinkedIn a very short moment to render the menu.
                _sleep(
                    page,
                    deadline=deadline,
                    milliseconds=120,
                )

                print(
                    "ELLIPSIS clicked"
                )
                return True

        except LinkedInProfileActionTimeout:
            raise

        except Exception as exc:
            print(
                "ELLIPSIS selector error:",
                f"{type(exc).__name__}: {exc}",
            )

    print(
        "ELLIPSIS: no overflow button found"
    )
    return False


def _click_more_button(
    page: Page,
    *,
    deadline: float,
) -> bool:
    """
    Click More của profile chính.

    Không dùng x/y.
    Không dùng Message/Follow để suy ra action row.
    Không thay đổi PATH direct Connect hay các action khác.

    LinkedIn có nhiều "More" trên page, nhưng More của profile
    nằm trong <main>, còn More của global navigation nằm ngoài <main>.

    Strategy:
    1. Scope vào <main>
    2. Tìm exact text "More"
    3. Leo lên ancestor <button> gần nhất
    4. Chỉ nhận button có aria-expanded
    5. Click button đó
    6. Verify aria-expanded=true hoặc exact custom-invite
       của profile hiện tại xuất hiện.
    """
    _check_deadline(deadline)

    vanity_name = _get_profile_vanity_name(page)

    for attempt in range(1, MORE_MAX_ATTEMPTS + 1):
        print(
            f"MORE attempt {attempt}/{MORE_MAX_ATTEMPTS}"
        )

        try:
            main = page.locator("main")

            if main.count() == 0:
                print("MORE: <main> not found")
                return False

            more_texts = main.get_by_text(
                "More",
                exact=True,
            )

            buttons = []
            seen = set()

            for index in range(more_texts.count()):
                _check_deadline(deadline)

                node = more_texts.nth(index)

                if not _is_visible_locator(
                    node,
                    deadline=deadline,
                    maximum_ms=180,
                ):
                    continue

                button = node.locator(
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

                try:
                    aria_expanded = button.get_attribute(
                        "aria-expanded"
                    )
                except Exception:
                    aria_expanded = None

                if aria_expanded is None:
                    continue

                # DOM identity dedupe; no coordinates.
                try:
                    key = button.evaluate(
                        """
                        (el) => {
                            if (!el.dataset.outreachMoreKey) {
                                el.dataset.outreachMoreKey =
                                    Math.random().toString(36).slice(2);
                            }
                            return el.dataset.outreachMoreKey;
                        }
                        """
                    )
                except Exception:
                    key = str(index)

                if key in seen:
                    continue

                seen.add(key)
                buttons.append(button)

            print(
                "MORE: profile candidates inside <main> =",
                len(buttons),
            )

            if not buttons:
                print(
                    "MORE: no button[aria-expanded] with exact text More inside <main>"
                )
                return False

            for candidate_index, button in enumerate(
                buttons,
                start=1,
            ):
                try:
                    current_state = (
                        button.get_attribute("aria-expanded")
                        or ""
                    ).strip().lower()
                except Exception:
                    current_state = ""

                print(
                    "MORE profile candidate",
                    candidate_index,
                    "aria-expanded=",
                    current_state,
                )

                if current_state == "true":
                    print("MORE already open")
                    return True

                if not _click_locator(
                    button,
                    deadline=deadline,
                    maximum_ms=500,
                ):
                    print(
                        "MORE profile candidate click failed"
                    )
                    continue

                verify_deadline = min(
                    deadline,
                    time.monotonic()
                    + (MORE_VERIFY_WINDOW_MS / 1000),
                )

                while time.monotonic() < verify_deadline:
                    _check_deadline(deadline)

                    try:
                        expanded = (
                            button.get_attribute(
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

                    if vanity_name:
                        try:
                            links = page.locator(
                                (
                                    "a[href*='/preload/custom-invite/']"
                                    f"[href*='vanityName={vanity_name}']"
                                )
                            )

                            for link_index in range(
                                links.count()
                            ):
                                link = links.nth(link_index)

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

                print(
                    "MORE: click completed but menu was not confirmed"
                )

        except LinkedInProfileActionTimeout:
            raise

        except Exception as exc:
            print(
                "MORE error:",
                f"{type(exc).__name__}: {exc}",
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
    exact text Connect -> closest <a>/<button>.

    Không dùng bất kỳ logic vị trí nào.
    Nếu clickable có custom-invite href thì bắt buộc vanityName
    phải khớp profile hiện tại.
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
            # bắt buộc đúng profile hiện tại.
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


def _click_connect_once(
    page: Page,
    *,
    deadline: float,
) -> bool:
    """
    Keep all three UI cases independent:

    CASE 1:
        direct Connect

    CASE 2:
        three-dot / overflow button -> Connect

    CASE 3:
        text More button -> Connect

    Opening one case must not replace or disable the others.
    """
    print(
        "Checking CASE 1: direct Connect"
    )

    if _click_direct_connect(
        page,
        deadline=deadline,
    ):
        return True

    # -----------------------------------------------------
    # CASE 2: existing three-dot / overflow path
    # -----------------------------------------------------
    print(
        "Checking CASE 2: three-dot / overflow menu"
    )

    if _click_ellipsis_button(
        page,
        deadline=deadline,
    ):
        print(
            "CASE 2 menu opened; checking custom-invite"
        )

        if _click_connect_via_custom_invite(
            page,
            deadline=deadline,
        ):
            return True

        print(
            "CASE 2: checking exact Connect text"
        )

        if _click_connect_via_menu_text(
            page,
            deadline=deadline,
        ):
            return True

        print(
            "CASE 2: Connect not found in overflow menu"
        )

    # -----------------------------------------------------
    # CASE 3: new text-More path
    # -----------------------------------------------------
    print(
        "Checking CASE 3: text More menu"
    )

    if not _click_more_button(
        page,
        deadline=deadline,
    ):
        print(
            "CASE 3: More button not opened"
        )
        return False

    print(
        "CASE 3 menu opened; checking custom-invite"
    )

    if _click_connect_via_custom_invite(
        page,
        deadline=deadline,
    ):
        return True

    print(
        "CASE 3: checking exact Connect text"
    )

    if _click_connect_via_menu_text(
        page,
        deadline=deadline,
    ):
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
