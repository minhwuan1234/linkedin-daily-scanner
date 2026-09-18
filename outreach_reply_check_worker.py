"""Scan LinkedIn Messaging > Unread for replies to sent outreach messages.

Flow:
    1. Open the selected Outreach LinkedIn profile.
    2. Open LinkedIn Messaging and select Unread.
    3. Read sender-name nodes only, without opening conversations.
    4. Compare those names with successfully sent targets for the account.
    5. Log exact matches without writing back to Supabase.

Keep other workers from using the same persistent browser profile while this
worker is running.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import time
import unicodedata
from collections.abc import Callable
from urllib.parse import unquote, urlparse

from playwright.sync_api import Frame, Locator, Page

from app.outreach_account_pool import OutreachAccountPool
from app.outreach_message_executor import get_outreach_supabase_client


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
UNREAD_NAME_SELECTORS = (
    ".msg-conversation-listitem__participant-names",
    ".msg-conversation-card__participant-names",
    ".msg-conversation-listitem__participant-name",
    (
        ".msg-conversations-container__conversations-list "
        '[data-anonymize="person-name"]'
    ),
    (
        ".msg-conversations-container__convo-list "
        '[data-anonymize="person-name"]'
    ),
)
UNREAD_LIST_SELECTORS = (
    ".msg-conversations-container__conversations-list",
    ".msg-conversations-container__convo-list",
    ".msg-conversations-container__conversations-list-container",
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


def _normalize_name(value: object) -> str:
    """Normalize accents, punctuation and whitespace for exact matching."""

    decomposed = unicodedata.normalize(
        "NFKD",
        str(value or "").strip(),
    )
    ascii_text = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    words = re.findall(r"[a-z0-9]+", ascii_text.casefold())
    return " ".join(words)


def _profile_name_from_linkedin_url(linkedin_url: object) -> str:
    """Derive a conservative full-name candidate from a public /in/ slug."""

    cleaned_url = str(linkedin_url or "").strip()
    if not cleaned_url:
        return ""

    try:
        path_parts = [
            part
            for part in urlparse(cleaned_url).path.split("/")
            if part
        ]
    except Exception:
        return ""

    if len(path_parts) < 2 or path_parts[0].casefold() != "in":
        return ""

    slug = unquote(path_parts[1]).strip().strip("-")

    # LinkedIn commonly appends a long numeric/hex identity token to a
    # readable profile slug. Remove only tokens that clearly look generated.
    slug = re.sub(
        r"(?:-[0-9]+)?-(?=[0-9a-z]*[0-9])[0-9a-z]{7,}$",
        "",
        slug,
        flags=re.IGNORECASE,
    )

    return _normalize_name(slug.replace("-", " "))


def load_sent_message_profiles(
    *,
    account_id: str,
    client=None,
) -> list[dict]:
    """Load only successfully sent targets for the active LinkedIn account."""

    active_client = client or get_outreach_supabase_client()
    response = (
        active_client.table("outreach_message_targets")
        .select(
            "id,prospect_id,assigned_account_id,linkedin_url,status,completed_at"
        )
        .eq("status", "sent")
        .eq("assigned_account_id", str(account_id).strip())
        .execute()
    )

    sent_profiles: list[dict] = []

    for raw_row in list(response.data or []):
        row = dict(raw_row)
        normalized_name = _profile_name_from_linkedin_url(
            row.get("linkedin_url")
        )
        if not normalized_name:
            continue
        row["normalized_name"] = normalized_name
        sent_profiles.append(row)

    logger.info(
        "Loaded sent message profiles | account=%s | count=%s",
        account_id,
        len(sent_profiles),
    )
    return sent_profiles


def _read_visible_unread_names(surface: Page | Frame) -> list[str]:
    """Read name nodes only; never read message previews or open a thread."""

    names: list[str] = []

    for selector in UNREAD_NAME_SELECTORS:
        try:
            candidates = surface.locator(selector)
            for index in range(candidates.count()):
                candidate = candidates.nth(index)
                if not _is_visible(candidate):
                    continue
                name = " ".join(candidate.inner_text().split())
                if name and name not in names:
                    names.append(name)
        except Exception:
            continue

    return names


def _scroll_unread_list(surface: Page | Frame) -> dict:
    """Scroll only the conversation list so lazy-loaded unread names appear."""

    return surface.evaluate(
        """
        ({listSelectors, nameSelectors}) => {
            let container = null;

            for (const selector of listSelectors) {
                const candidate = document.querySelector(selector);
                if (candidate && candidate.scrollHeight > candidate.clientHeight) {
                    container = candidate;
                    break;
                }
            }

            if (!container) {
                const nameNode = document.querySelector(nameSelectors.join(','));
                let candidate = nameNode ? nameNode.parentElement : null;

                while (candidate) {
                    const style = window.getComputedStyle(candidate);
                    const canScroll =
                        (style.overflowY === 'auto' || style.overflowY === 'scroll') &&
                        candidate.scrollHeight > candidate.clientHeight;
                    if (canScroll) {
                        container = candidate;
                        break;
                    }
                    candidate = candidate.parentElement;
                }
            }

            if (!container) {
                return {found: false, atBottom: true, top: 0};
            }

            const before = container.scrollTop;
            container.scrollTop = Math.min(
                container.scrollTop + Math.max(container.clientHeight * 0.8, 240),
                container.scrollHeight
            );
            container.dispatchEvent(new Event('scroll', {bubbles: true}));

            const maximum = Math.max(
                0,
                container.scrollHeight - container.clientHeight
            );

            return {
                found: true,
                atBottom: container.scrollTop >= maximum - 2,
                top: container.scrollTop,
                moved: container.scrollTop !== before
            };
        }
        """,
        {
            "listSelectors": list(UNREAD_LIST_SELECTORS),
            "nameSelectors": list(UNREAD_NAME_SELECTORS),
        },
    )


def scan_unread_names(page: Page) -> list[str]:
    """Collect all currently listed Unread sender names without opening them."""

    surface = _find_unread_surface(page)
    if surface is None:
        _log_unread_diagnostics(page)
        raise RuntimeError("Unread filter surface disappeared before scanning.")

    names: list[str] = []
    bottom_passes = 0

    for _ in range(40):
        before_count = len(names)

        for name in _read_visible_unread_names(surface):
            if name not in names:
                names.append(name)

        scroll_state = _scroll_unread_list(surface)
        at_bottom = bool(scroll_state.get("atBottom"))

        if at_bottom and len(names) == before_count:
            bottom_passes += 1
        else:
            bottom_passes = 0

        if bottom_passes >= 2:
            break

        page.wait_for_timeout(500)

    logger.info(
        "Unread names scanned | count=%s | names=%s",
        len(names),
        names,
    )
    return names


def log_sent_name_matches(
    *,
    unread_names: list[str],
    sent_profiles: list[dict],
) -> int:
    """Log exact normalized full-name matches against sent targets."""

    sent_by_name: dict[str, list[dict]] = {}
    for sent_profile in sent_profiles:
        normalized_name = str(
            sent_profile.get("normalized_name") or ""
        ).strip()
        if normalized_name:
            sent_by_name.setdefault(normalized_name, []).append(sent_profile)

    matched_count = 0

    for unread_name in unread_names:
        normalized_unread_name = _normalize_name(unread_name)
        matches = sent_by_name.get(normalized_unread_name, [])
        if not matches:
            continue

        matched_count += 1
        logger.warning(
            "REPLY MATCH | unread_name=%s | sent_target_ids=%s",
            unread_name,
            [str(match.get("id") or "") for match in matches],
        )

    logger.info(
        "Reply-check summary | unread_names=%s | matched_sent_names=%s",
        len(unread_names),
        matched_count,
    )
    return matched_count


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
    """Open Unread and report names that match successfully sent targets."""

    pool = OutreachAccountPool()
    account = pool.get_account(account_id)
    browser = account.create_browser_manager()
    client = get_outreach_supabase_client()

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
        sent_profiles = load_sent_message_profiles(
            account_id=account.account_id,
            client=client,
        )
        unread_names = scan_unread_names(page)
        matched_count = log_sent_name_matches(
            unread_names=unread_names,
            sent_profiles=sent_profiles,
        )

        print("")
        print("Reply-check scan completed.")
        print(f"Unread names: {len(unread_names)}")
        print(f"Matched sent profiles: {matched_count}")
        print("Matching names were written to the worker log.")
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
