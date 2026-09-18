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
import re
import time
from collections.abc import Callable

from playwright.sync_api import Page

from app.outreach_account_pool import OutreachAccountPool


DEFAULT_ACCOUNT_ID = "outreach_account_02"
LINKEDIN_HOME_URL = "https://www.linkedin.com/"
LINKEDIN_MESSAGING_URL = "https://www.linkedin.com/messaging/"

logger = logging.getLogger("outreach_reply_check_worker")


def _click_first_visible(
    page: Page,
    candidates: list[Callable[[Page], object]],
    *,
    description: str,
    timeout_ms: int = 3_000,
) -> None:
    """Click the first visible candidate selector."""

    for build_locator in candidates:
        locator = build_locator(page)

        try:
            locator.first.wait_for(
                state="visible",
                timeout=timeout_ms,
            )
            locator.first.scroll_into_view_if_needed()
            locator.first.click()
            logger.info("Clicked %s", description)
            return
        except Exception:
            continue

    raise RuntimeError(
        f"Could not find the LinkedIn {description} control."
    )


def open_messaging(page: Page) -> None:
    """Open Messaging from LinkedIn navigation."""

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

    if "/messaging" not in (page.url or "").lower():
        page.wait_for_timeout(1_000)

    if "/messaging" not in (page.url or "").lower():
        page.goto(
            LINKEDIN_MESSAGING_URL,
            wait_until="domcontentloaded",
        )

    page.wait_for_timeout(1_000)


def open_unread(page: Page) -> None:
    """Click Unread inside LinkedIn Messaging."""

    candidates = [
        lambda active_page: active_page.locator(
            'button[data-test-messaging-inbox-filters__filter-pill="UNREAD"]'
        ),
        lambda active_page: active_page.locator(
            'button:has-text("Unread")'
        ),
        lambda active_page: active_page.locator(
            'a:has-text("Unread")'
        ),
        lambda active_page: active_page.locator(
            '[role="button"]:has-text("Unread")'
        ),
        lambda active_page: active_page.get_by_text(
            re.compile(r"^\s*Unread\s*$", re.IGNORECASE)
        ),
        lambda active_page: active_page.get_by_role(
            "button", name="Unread", exact=True
        ),
        lambda active_page: active_page.get_by_role(
            "link", name="Unread", exact=True
        ),
        lambda active_page: active_page.locator(
            '[aria-label="Unread"]'
        ),
        lambda active_page: active_page.get_by_text(
            "Unread", exact=True
        ),
    ]

    _click_first_visible(
        page,
        candidates,
        description="Unread",
        timeout_ms=30_000,
    )
    page.wait_for_timeout(1_000)


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
        open_messaging(page)
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
