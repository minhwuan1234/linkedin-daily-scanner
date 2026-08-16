from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError

from app.linkedin_browser import (
    LinkedInBrowserManager,
    LinkedInBrowserTimeoutError,
    LinkedInSessionError,
)


PROFILE_TIMEOUT_MS = 15_000
ELLIPSIS_MENU_WAIT_MS = 1_500
STATE_POLL_MS = 120

AcceptanceStatus = Literal[
    "pending",
    "accepted",
    "declined_or_unknown",
    "check_failed",
]


@dataclass(frozen=True)
class LinkedInAcceptanceResult:
    linkedin_url: str
    final_url: str
    status: AcceptanceStatus
    message: str


class LinkedInAcceptanceCheckTimeout(RuntimeError):
    pass


def _build_deadline() -> float:
    return time.monotonic() + (PROFILE_TIMEOUT_MS / 1000)


def _check_deadline(deadline: float) -> None:
    if time.monotonic() >= deadline:
        raise LinkedInAcceptanceCheckTimeout(
            "Acceptance check exceeded the profile timeout."
        )


def _remaining_ms(deadline: float, *, maximum_ms: int) -> int:
    remaining = int((deadline - time.monotonic()) * 1000)
    if remaining <= 0:
        raise LinkedInAcceptanceCheckTimeout(
            "Acceptance check exceeded the profile timeout."
        )
    return max(1, min(remaining, maximum_ms))


def _sleep(page: Page, *, deadline: float, milliseconds: int) -> None:
    page.wait_for_timeout(
        _remaining_ms(deadline, maximum_ms=milliseconds)
    )


def _is_visible_locator(
    locator: Locator,
    *,
    deadline: float,
    maximum_ms: int = 180,
) -> bool:
    _check_deadline(deadline)
    try:
        return locator.is_visible(
            timeout=_remaining_ms(deadline, maximum_ms=maximum_ms)
        )
    except LinkedInAcceptanceCheckTimeout:
        raise
    except Exception:
        return False


def _click_locator(
    locator: Locator,
    *,
    deadline: float,
    maximum_ms: int = 500,
) -> bool:
    """Only used to open the ellipsis menu."""
    _check_deadline(deadline)

    try:
        locator.click(
            timeout=_remaining_ms(deadline, maximum_ms=maximum_ms)
        )
        return True
    except Exception:
        pass

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
    except LinkedInAcceptanceCheckTimeout:
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
    """
    CASE 1: current profile visibly shows Pending.
    Scope to <main> to avoid unrelated Pending text elsewhere.
    """
    _check_deadline(deadline)

    main = page.locator("main")
    if main.count() == 0:
        print("ACCEPTANCE PENDING: <main> not found")
        return False

    selectors = (
        "button:has-text('Pending')",
        "[role='button']:has-text('Pending')",
        "a:has-text('Pending')",
        "[aria-label*='Pending']",
        "[aria-label*='pending']",
    )

    for selector in selectors:
        _check_deadline(deadline)
        try:
            candidates = main.locator(selector)
            for index in range(candidates.count()):
                candidate = candidates.nth(index)
                if not _is_visible_locator(
                    candidate,
                    deadline=deadline,
                    maximum_ms=140,
                ):
                    continue

                try:
                    text_value = " ".join(
                        (candidate.inner_text() or "").split()
                    ).strip().lower()
                except Exception:
                    text_value = ""

                try:
                    aria_label = (
                        candidate.get_attribute("aria-label") or ""
                    ).strip().lower()
                except Exception:
                    aria_label = ""

                if text_value == "pending" or "pending" in aria_label:
                    print("ACCEPTANCE STATE: pending")
                    return True

        except LinkedInAcceptanceCheckTimeout:
            raise
        except Exception:
            continue

    return False


def _wait_for_visible_menu(page: Page, *, deadline: float) -> bool:
    wait_deadline = min(
        deadline,
        time.monotonic() + (ELLIPSIS_MENU_WAIT_MS / 1000),
    )

    while time.monotonic() < wait_deadline:
        _check_deadline(deadline)
        try:
            menus = page.locator("[role='menu']")
            for index in range(menus.count()):
                if _is_visible_locator(
                    menus.nth(index),
                    deadline=deadline,
                    maximum_ms=100,
                ):
                    return True
        except LinkedInAcceptanceCheckTimeout:
            raise
        except Exception:
            pass

        _sleep(page, deadline=deadline, milliseconds=STATE_POLL_MS)

    return False


def _open_acceptance_ellipsis_menu(
    page: Page,
    *,
    deadline: float,
) -> bool:
    """
    Acceptance-checker-specific ellipsis opener.

    Completely separate from linkedin_connect_action.py.
    It never calls CASE 2 or CASE 3 Connect functions.
    """
    _check_deadline(deadline)

    selectors = (
        "button[aria-label='More actions']",
        "button[aria-label*='More actions']",
        "button[aria-label='More']",
        "button[title='More actions']",
        "button[title='More']",
    )

    seen: set[str] = set()

    for selector in selectors:
        _check_deadline(deadline)
        try:
            candidates = page.locator(selector)

            for index in range(candidates.count()):
                button = candidates.nth(index)

                if not _is_visible_locator(
                    button,
                    deadline=deadline,
                    maximum_ms=180,
                ):
                    continue

                try:
                    visible_text = (
                        button.inner_text() or ""
                    ).strip().lower()
                except Exception:
                    visible_text = ""

                # Keep text-More behavior separate.
                if visible_text == "more":
                    continue

                try:
                    key = button.evaluate(
                        """
                        (el) => {
                            if (!el.dataset.acceptanceEllipsisKey) {
                                el.dataset.acceptanceEllipsisKey =
                                    Math.random().toString(36).slice(2);
                            }
                            return el.dataset.acceptanceEllipsisKey;
                        }
                        """
                    )
                except Exception:
                    key = f"{selector}:{index}"

                if key in seen:
                    continue
                seen.add(key)

                try:
                    expanded = (
                        button.get_attribute("aria-expanded") or ""
                    ).strip().lower()
                except Exception:
                    expanded = ""

                if expanded == "true":
                    print("ACCEPTANCE ELLIPSIS: menu already open")
                    return True

                if not _click_locator(
                    button,
                    deadline=deadline,
                    maximum_ms=500,
                ):
                    continue

                print("ACCEPTANCE ELLIPSIS: clicked")

                if _wait_for_visible_menu(page, deadline=deadline):
                    print(
                        "ACCEPTANCE ELLIPSIS: visible role=menu confirmed"
                    )
                    return True

                print(
                    "ACCEPTANCE ELLIPSIS: click completed "
                    "but menu was not confirmed"
                )

        except LinkedInAcceptanceCheckTimeout:
            raise
        except Exception as exc:
            print(
                "ACCEPTANCE ELLIPSIS error:",
                f"{type(exc).__name__}: {exc}",
            )

    return False


def _has_remove_connection_in_visible_menu(
    page: Page,
    *,
    deadline: float,
) -> bool:
    """
    CASE 2: accepted.

    Inspect ONLY visible role=menu containers and exact
    role=menuitem text "Remove connection".

    Never clicks Remove connection.
    """
    _check_deadline(deadline)

    menus = page.locator("[role='menu']")
    visible_menu_found = False

    for menu_index in range(menus.count()):
        menu = menus.nth(menu_index)
        if not _is_visible_locator(
            menu,
            deadline=deadline,
            maximum_ms=120,
        ):
            continue

        visible_menu_found = True
        menuitems = menu.locator("[role='menuitem']")

        for item_index in range(menuitems.count()):
            item = menuitems.nth(item_index)

            if not _is_visible_locator(
                item,
                deadline=deadline,
                maximum_ms=120,
            ):
                continue

            try:
                text_value = " ".join(
                    (item.inner_text() or "").split()
                ).strip()
            except Exception:
                text_value = ""

            print(
                "ACCEPTANCE MENUITEM:",
                item_index,
                repr(text_value),
            )

            if text_value.lower() == "remove connection":
                print(
                    "ACCEPTANCE STATE: accepted "
                    "(Remove connection found)"
                )
                return True

    if not visible_menu_found:
        raise RuntimeError(
            "Acceptance ellipsis menu is not visible."
        )

    return False


def check_profile_acceptance(
    *,
    browser: LinkedInBrowserManager,
    linkedin_url: str,
) -> LinkedInAcceptanceResult:
    """
    Read-only acceptance checker.

    1. Pending visible
       -> pending

    2. No Pending + ellipsis menu contains exact Remove connection
       -> accepted

    3. No Pending + menu opened + no Remove connection
       -> declined_or_unknown

    4. Technical/session/navigation/menu failure
       -> check_failed
    """
    cleaned_url = str(linkedin_url or "").strip()

    if not cleaned_url:
        return LinkedInAcceptanceResult(
            linkedin_url="",
            final_url="",
            status="check_failed",
            message="invalid_url: LinkedIn URL cannot be empty.",
        )

    deadline = _build_deadline()
    page: Page | None = None

    try:
        print("")
        print("=" * 60)
        print("LINKEDIN ACCEPTANCE CHECK")
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
            return LinkedInAcceptanceResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="check_failed",
                message=(
                    "url_not_found: LinkedIn profile does not exist "
                    "or is unavailable."
                ),
            )

        # CASE 1: still pending.
        if _has_pending_state(page, deadline=deadline):
            return LinkedInAcceptanceResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="pending",
                message="Connection invitation is still pending.",
            )

        # CASE 2 / CASE 3: inspect the ellipsis menu.
        if not _open_acceptance_ellipsis_menu(
            page,
            deadline=deadline,
        ):
            return LinkedInAcceptanceResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="check_failed",
                message=(
                    "menu_error: Could not open the profile "
                    "ellipsis menu."
                ),
            )

        if _has_remove_connection_in_visible_menu(
            page,
            deadline=deadline,
        ):
            return LinkedInAcceptanceResult(
                linkedin_url=cleaned_url,
                final_url=page.url,
                status="accepted",
                message=(
                    "Connection accepted: 'Remove connection' "
                    "is visible in the profile menu."
                ),
            )

        return LinkedInAcceptanceResult(
            linkedin_url=cleaned_url,
            final_url=page.url,
            status="declined_or_unknown",
            message=(
                "Pending is no longer visible and "
                "'Remove connection' was not found."
            ),
        )

    except (
        LinkedInAcceptanceCheckTimeout,
        LinkedInBrowserTimeoutError,
        PlaywrightTimeoutError,
    ) as exc:
        return LinkedInAcceptanceResult(
            linkedin_url=cleaned_url,
            final_url=page.url if page is not None else "",
            status="check_failed",
            message=f"timeout: acceptance check failed. {exc}",
        )

    except LinkedInSessionError as exc:
        return LinkedInAcceptanceResult(
            linkedin_url=cleaned_url,
            final_url=page.url if page is not None else "",
            status="check_failed",
            message=f"session_error: {exc}",
        )

    except Exception as exc:
        return LinkedInAcceptanceResult(
            linkedin_url=cleaned_url,
            final_url=page.url if page is not None else "",
            status="check_failed",
            message=(
                "acceptance_error: "
                f"{type(exc).__name__}: {exc}"
            ),
        )
