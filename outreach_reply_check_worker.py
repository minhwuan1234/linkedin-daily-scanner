"""Open LinkedIn Messaging > Unread for the reply-check worker.

Phase 1 only:
    1. Open the selected Outreach LinkedIn profile.
    2. Open LinkedIn Messaging.
    3. Click Unread.

This worker deliberately does not read or write Supabase yet.  It also does
not inspect conversations or send messages.  Keep other workers from using
the same persistent browser profile while this worker is running.
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from collections.abc import Callable

from playwright.sync_api import Frame, Locator, Page

from app.outreach_account_pool import OutreachAccountPool


DEFAULT_ACCOUNT_ID = "outreach_account_02"
LINKEDIN_HOME_URL = "https://www.linkedin.com/"
LINKEDIN_MESSAGING_URL = "https://www.linkedin.com/messaging/"

logger = logging.getLogger("outreach_reply_check_worker")

UNREAD_SELECTOR = (
    'button[data-test-messaging-inbox-filters__filter-pill="UNREAD"]'
)
UNREAD_CONTAINER_SELECTOR = (
    "div.msg-conversations-container__title-row"
)


def _is_visible(locator: Locator, *, timeout_ms: int = 500) -> bool:
    """Mirror the proven visibility check used by the old workers."""

    try:
        return locator.is_visible(timeout=timeout_ms)
    except Exception:
        return False


def _click_locator(locator: Locator, *, timeout_ms: int = 3_000) -> bool:
    """Use the old worker's DOM-click-first strategy with a fallback."""

    try:
        locator.evaluate(
            """
            element => {
                element.scrollIntoView({block: 'center', inline: 'center'});
                element.click();
            }
            """
        )
        return True
    except Exception:
        pass

    try:
        locator.click(timeout=timeout_ms, force=True)
        return True
    except Exception:
        return False


def _is_selected(locator: Locator) -> bool:
    try:
        return (
            locator.get_attribute("aria-pressed") == "true"
            or locator.get_attribute("aria-checked") == "true"
        )
    except Exception:
        return False


def _surface_has_unread(surface: Page | Frame) -> bool:
    try:
        return surface.locator(UNREAD_SELECTOR).count() > 0
    except Exception:
        return False


def _messaging_surfaces(page: Page) -> list[Page]:
    """Prefer the page just used, then inspect newer tabs before old tabs."""

    surfaces: list[Page] = []
    if not page.is_closed():
        surfaces.append(page)

    for candidate in reversed(page.context.pages):
        if candidate.is_closed() or candidate in surfaces:
            continue
        surfaces.append(candidate)

    return surfaces


def _find_unread_surface(page: Page) -> Page | Frame | None:
    """Return only a live surface whose DOM actually contains Unread."""

    for candidate_page in _messaging_surfaces(page):
        if _surface_has_unread(candidate_page):
            return candidate_page

        for frame in candidate_page.frames:
            if frame is candidate_page.main_frame:
                continue
            if _surface_has_unread(frame):
                return frame

    return None


def _log_unread_diagnostics(page: Page) -> None:
    """Log non-sensitive DOM diagnostics instead of private message text."""

    for page_index, candidate_page in enumerate(
        _messaging_surfaces(page)
    ):
        try:
            exact_count = candidate_page.locator(
                UNREAD_SELECTOR
            ).count()
            text_count = candidate_page.locator(
                'button:has-text("Unread")'
            ).count()
            logger.error(
                "Unread diagnostics | page=%s | url=%s | exact=%s | text=%s",
                page_index,
                candidate_page.url,
                exact_count,
                text_count,
            )
        except Exception as exc:
            logger.error(
                "Unread diagnostics failed | page=%s | error=%s: %s",
                page_index,
                type(exc).__name__,
                exc,
            )

        for frame_index, frame in enumerate(candidate_page.frames):
            if frame is candidate_page.main_frame:
                continue
            try:
                logger.error(
                    "Unread diagnostics | page=%s | frame=%s | url=%s | exact=%s",
                    page_index,
                    frame_index,
                    frame.url,
                    frame.locator(UNREAD_SELECTOR).count(),
                )
            except Exception:
                continue


def _click_first_visible(
    page: Page,
    candidates: list[Callable[[Page], Locator]],
    *,
    description: str,
    timeout_ms: int = 3_000,
) -> None:
    """Use the proven old-worker flow across every matching candidate."""

    for build_locator in candidates:
        locator = build_locator(page)

        try:
            for index in range(locator.count()):
                candidate = locator.nth(index)
                if not _is_visible(candidate):
                    continue
                if _click_locator(candidate, timeout_ms=timeout_ms):
                    logger.info("Clicked %s", description)
                    return
        except Exception:
            continue

    raise RuntimeError(
        f"Could not find the LinkedIn {description} control."
    )


def open_messaging(page: Page) -> Page:
    """Open Messaging and return the page that owns the messaging UI."""

    candidates = [
        lambda active_page: active_page.get_by_role(
            "link", name="Messaging", exact=True
        ),
        lambda active_page: active_page.get_by_role(
            "button", name="Messaging", exact=True
        ),
        lambda active_page: active_page.locator(
            'a[href*="/messaging/"]'
        ),
        lambda active_page: active_page.get_by_text(
            "Messaging", exact=True
        ),
    ]

    try:
        _click_first_visible(
            page,
            candidates,
            description="Messaging",
        )
    except RuntimeError:
        # LinkedIn can hide the global nav at narrower widths.  The direct
        # route is only a navigation fallback; Unread is still clicked
        # as a UI control in the next step.
        logger.info(
            "Messaging nav item was not visible; opening its LinkedIn route."
        )
        page.goto(
            LINKEDIN_MESSAGING_URL,
            wait_until="domcontentloaded",
        )

    # Keep the same Page whenever possible. The old implementation returned
    # the first /messaging tab in the persistent context, which could be a
    # stale restored tab while the visible UI belonged to another page.
    for _ in range(40):
        surface = _find_unread_surface(page)
        if surface is not None:
            owner_page = surface if isinstance(surface, Page) else surface.page
            owner_page.bring_to_front()
            logger.info(
                "Messaging filters found | url=%s",
                owner_page.url,
            )
            return owner_page

        page.wait_for_timeout(500)

    if "/messaging" not in (page.url or "").lower():
        logger.info(
            "Messaging UI did not settle after click; opening direct route."
        )
        page.goto(
            LINKEDIN_MESSAGING_URL,
            wait_until="domcontentloaded",
        )

    for _ in range(40):
        surface = _find_unread_surface(page)
        if surface is not None:
            owner_page = surface if isinstance(surface, Page) else surface.page
            owner_page.bring_to_front()
            logger.info(
                "Messaging filters found after direct navigation | url=%s",
                owner_page.url,
            )
            return owner_page
        page.wait_for_timeout(500)

    _log_unread_diagnostics(page)
    return page


def open_unread(page: Page) -> None:
    """Click Unread inside LinkedIn Messaging."""

    deadline = time.monotonic() + 30
    selectors = (
        UNREAD_SELECTOR,
        (
            f'{UNREAD_CONTAINER_SELECTOR} '
            'button[data-test-messaging-inbox-filters__filter-pill="UNREAD"]'
        ),
        'button[role="button"]:has-text("Unread")',
        '[role="button"]:has-text("Unread")',
        'button:has-text("Unread")',
    )

    while time.monotonic() < deadline:
        surface = _find_unread_surface(page)

        if surface is None:
            page.wait_for_timeout(250)
            continue

        for selector in selectors:
            try:
                candidates = surface.locator(selector)
                for index in range(candidates.count()):
                    candidate = candidates.nth(index)

                    if not _is_visible(candidate):
                        continue

                    if _is_selected(candidate):
                        logger.info("Unread filter is already selected")
                        return

                    if not _click_locator(candidate):
                        continue

                    logger.info(
                        "Clicked Unread | selector=%s | candidate=%s",
                        selector,
                        index,
                    )

                    for _ in range(20):
                        if _is_selected(candidate):
                            logger.info("Unread filter selection confirmed")
                            return
                        page.wait_for_timeout(100)

            except Exception:
                continue

        page.wait_for_timeout(250)

    _log_unread_diagnostics(page)
    raise RuntimeError(
        "Could not find and confirm the LinkedIn Unread control."
    )


def run_once(account_id: str) -> None:
    """Run the phase-one navigation for one Outreach account."""

    pool = OutreachAccountPool()
    account = pool.get_account(account_id)
    browser = account.create_browser_manager()

    logger.info(
        "Starting reply-check worker | account=%s | profile=%s",
        account.account_id,
        account.profile_directory,
    )

    try:
        browser.start()
        page = browser.open_linkedin_url(LINKEDIN_HOME_URL)
        page = open_messaging(page)
        open_unread(page)

        print("")
        print("Reply-check worker phase 1 completed.")
        print("LinkedIn Messaging > Unread is open.")
        print("The browser will stay open. Press Ctrl+C to stop.")

        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Reply-check worker stopped.")
    finally:
        browser.stop()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Open LinkedIn Messaging > Unread for reply checking."
        )
    )
    parser.add_argument(
        "--account-id",
        default=os.getenv(
            "OUTREACH_REPLY_CHECK_ACCOUNT_ID",
            DEFAULT_ACCOUNT_ID,
        ),
        help=(
            "Outreach account whose persistent LinkedIn profile is used "
            f"(default: {DEFAULT_ACCOUNT_ID})."
        ),
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    args = _parse_args()
    run_once(str(args.account_id).strip())


if __name__ == "__main__":
    main()
