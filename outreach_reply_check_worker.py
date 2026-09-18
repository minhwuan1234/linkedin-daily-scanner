"""Scan LinkedIn Messaging > Unread for replies to sent outreach messages.

Flow:
    1. Open the selected Outreach LinkedIn profile.
    2. Open LinkedIn Messaging and select Unread.
    3. Compare unread sender names with successfully sent targets.
    4. Open only the conversations verified by that comparison.
    5. Log the incoming reply text with its database evidence.
    6. Use the active-thread menu beside Star to restore Mark as unread.

This worker is read-only with respect to Supabase. Opening a conversation
changes LinkedIn UI state, so it restores the unread state before continuing.

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
from difflib import SequenceMatcher
from urllib.parse import unquote, urlparse

from playwright.sync_api import Frame, Locator, Page

from app.outreach_account_pool import OutreachAccountPool
from app.outreach_message_executor import get_outreach_supabase_client
from app.outreach_reply_store import save_outreach_reply


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
FUZZY_MATCH_THRESHOLD = 0.70
CONVERSATION_SETTLE_MS = 2_500
BEFORE_THREAD_MENU_MS = 1_200
THREAD_MENU_SETTLE_MS = 700
MARK_UNREAD_SETTLE_MS = 2_000
BETWEEN_CONVERSATIONS_MS = 1_500
MESSAGE_BODY_SELECTORS = (
    ".msg-s-event-listitem__body",
    ".msg-s-message-group__message-bubble",
    ".msg-s-event-listitem__message-bubble",
)
MESSAGE_AUTHOR_SELECTORS = (
    ".msg-s-message-group__name",
    '[data-anonymize="person-name"]',
)
MESSAGE_SCROLL_CONTAINER_SELECTORS = (
    ".msg-s-message-list-container",
    ".msg-s-message-list",
    ".msg-thread__messages",
    ".msg-s-message-list-content",
)
THREAD_STAR_SELECTORS = (
    'button[aria-label*="Star conversation"]',
    'button[aria-label="Star"]',
    'button:has(svg[data-test-icon*="star"])',
)
THREAD_OVERFLOW_SELECTORS = (
    "button.msg-thread-actions__control.artdeco-dropdown__trigger",
    (
        "button.msg-thread-actions__control:has("
        'span.visually-hidden:has-text("Open the options list in your conversation")'
        ")"
    ),
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
            (
                "id,prospect_id,assigned_account_id,linkedin_url,status,"
                "message_text,completed_at"
            )
        )
        .eq("status", "sent")
        .eq("assigned_account_id", str(account_id).strip())
        .order("completed_at", desc=True)
        .execute()
    )

    sent_profiles: list[dict] = []
    derivable_name_count = 0

    for raw_row in list(response.data or []):
        row = dict(raw_row)
        normalized_name = _profile_name_from_linkedin_url(
            row.get("linkedin_url")
        )
        row["normalized_name"] = normalized_name
        sent_profiles.append(row)

        if normalized_name:
            derivable_name_count += 1

    logger.info(
        (
            "DB SENT QUERY EVIDENCE | table=outreach_message_targets | "
            "filters=status:sent,assigned_account_id:%s | rows=%s | "
            "names_derived_from_linkedin_url=%s | names_not_derivable=%s"
        ),
        account_id,
        len(sent_profiles),
        derivable_name_count,
        len(sent_profiles) - derivable_name_count,
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
) -> list[dict]:
    """Log exact decisions with evidence from sent database records."""

    sent_by_name: dict[str, list[dict]] = {}
    for sent_profile in sent_profiles:
        normalized_name = str(
            sent_profile.get("normalized_name") or ""
        ).strip()
        if normalized_name:
            sent_by_name.setdefault(normalized_name, []).append(sent_profile)

    matched_profiles: list[dict] = []

    for unread_name in unread_names:
        normalized_unread_name = _normalize_name(unread_name)
        matches = sent_by_name.get(normalized_unread_name, [])

        logger.info(
            "UNREAD NAME EVIDENCE | raw_name=%s | normalized_name=%s",
            unread_name,
            normalized_unread_name,
        )

        if matches:
            best_match = matches[0]
            matched_profiles.append(
                {
                    "unread_name": unread_name,
                    "normalized_unread_name": normalized_unread_name,
                    "match_reason": "exact_normalized_name",
                    "similarity": 1.0,
                    "sent_profile": best_match,
                }
            )

            for match in matches:
                logger.warning(
                    (
                        "REPLY MATCH | reason=exact_normalized_name | "
                        "unread_name=%s | unread_normalized=%s | "
                        "db_target_id=%s | db_prospect_id=%s | "
                        "db_account_id=%s | db_status=%s | "
                        "db_completed_at=%s | db_linkedin_url=%s | "
                        "db_derived_name=%s"
                    ),
                    unread_name,
                    normalized_unread_name,
                    match.get("id"),
                    match.get("prospect_id"),
                    match.get("assigned_account_id"),
                    match.get("status"),
                    match.get("completed_at"),
                    match.get("linkedin_url"),
                    match.get("normalized_name"),
                )
            continue

        comparable_profiles = [
            profile
            for profile in sent_profiles
            if str(profile.get("normalized_name") or "").strip()
        ]
        ranked_profiles = sorted(
            comparable_profiles,
            key=lambda profile: SequenceMatcher(
                None,
                normalized_unread_name,
                str(profile.get("normalized_name") or ""),
            ).ratio(),
            reverse=True,
        )[:3]

        best_profile = ranked_profiles[0] if ranked_profiles else None
        best_similarity = (
            SequenceMatcher(
                None,
                normalized_unread_name,
                str(best_profile.get("normalized_name") or ""),
            ).ratio()
            if best_profile is not None
            else 0.0
        )

        if (
            best_profile is not None
            and best_similarity >= FUZZY_MATCH_THRESHOLD
        ):
            matched_profiles.append(
                {
                    "unread_name": unread_name,
                    "normalized_unread_name": normalized_unread_name,
                    "match_reason": "fuzzy_similarity_at_or_above_threshold",
                    "similarity": best_similarity,
                    "sent_profile": best_profile,
                }
            )
            logger.warning(
                (
                    "REPLY MATCH | reason=fuzzy_similarity_above_threshold | "
                    "threshold=>=%.2f | similarity=%.3f | "
                    "unread_name=%s | unread_normalized=%s | "
                    "db_target_id=%s | db_prospect_id=%s | "
                    "db_account_id=%s | db_status=%s | "
                    "db_completed_at=%s | db_linkedin_url=%s | "
                    "db_derived_name=%s"
                ),
                FUZZY_MATCH_THRESHOLD,
                best_similarity,
                unread_name,
                normalized_unread_name,
                best_profile.get("id"),
                best_profile.get("prospect_id"),
                best_profile.get("assigned_account_id"),
                best_profile.get("status"),
                best_profile.get("completed_at"),
                best_profile.get("linkedin_url"),
                best_profile.get("normalized_name"),
            )
            continue

        nearest_evidence = [
            {
                "target_id": profile.get("id"),
                "prospect_id": profile.get("prospect_id"),
                "account_id": profile.get("assigned_account_id"),
                "status": profile.get("status"),
                "completed_at": profile.get("completed_at"),
                "linkedin_url": profile.get("linkedin_url"),
                "derived_name": profile.get("normalized_name"),
                "similarity": round(
                    SequenceMatcher(
                        None,
                        normalized_unread_name,
                        str(profile.get("normalized_name") or ""),
                    ).ratio(),
                    3,
                ),
            }
            for profile in ranked_profiles
        ]

        logger.warning(
            (
                "NO REPLY MATCH | "
                "reason=no_exact_match_and_best_similarity_below_threshold | "
                "unread_name=%s | unread_normalized=%s | "
                "required_similarity=>=%.2f | best_similarity=%.3f | "
                "db_sent_row_count=%s | nearest_db_evidence=%s"
            ),
            unread_name,
            normalized_unread_name,
            FUZZY_MATCH_THRESHOLD,
            best_similarity,
            len(sent_profiles),
            nearest_evidence,
        )

    logger.info(
        "Reply-check summary | unread_names=%s | matched_sent_names=%s",
        len(unread_names),
        len(matched_profiles),
    )
    return matched_profiles


def _find_visible_unread_name(
    surface: Page | Frame,
    unread_name: str,
) -> Locator | None:
    expected_name = _normalize_name(unread_name)

    for selector in UNREAD_NAME_SELECTORS:
        try:
            candidates = surface.locator(selector)
            for index in range(candidates.count()):
                candidate = candidates.nth(index)
                if not _is_visible(candidate):
                    continue
                actual_name = _normalize_name(candidate.inner_text())
                if actual_name == expected_name:
                    return candidate
        except Exception:
            continue

    return None


def _scroll_unread_list_to_start(surface: Page | Frame) -> None:
    try:
        surface.evaluate(
            """
            selectors => {
                for (const selector of selectors) {
                    const candidate = document.querySelector(selector);
                    if (candidate) {
                        candidate.scrollTop = 0;
                        candidate.dispatchEvent(
                            new Event('scroll', {bubbles: true})
                        );
                    }
                }
            }
            """,
            list(UNREAD_LIST_SELECTORS),
        )
    except Exception:
        pass


def _click_conversation_name(name_locator: Locator) -> bool:
    # The visible participant-name div itself owns the LinkedIn row click.
    # Click that exact matched-name node first instead of guessing an ancestor.
    if _click_locator(name_locator):
        logger.info(
            "CONVERSATION CLICK EVIDENCE | strategy=matched-name-node"
        )
        return True

    ancestor_selectors = (
        'xpath=ancestor::a[contains(@href,"/messaging/thread/")][1]',
        (
            'xpath=ancestor::li['
            'contains(@class,"msg-conversation-listitem")][1]'
        ),
        (
            'xpath=ancestor::*['
            'contains(@class,"msg-conversation-card")][1]'
        ),
        'xpath=ancestor::*[@role="button"][1]',
    )

    for selector in ancestor_selectors:
        try:
            candidate = name_locator.locator(selector)
            if candidate.count() <= 0:
                continue
            candidate = candidate.first
            if _is_visible(candidate) and _click_locator(candidate):
                logger.info(
                    "CONVERSATION CLICK EVIDENCE | strategy=ancestor | selector=%s",
                    selector,
                )
                return True
        except Exception:
            continue

    return _click_locator(name_locator)


def open_matched_conversation(page: Page, unread_name: str) -> None:
    """Open one matched Unread row by exact normalized visible name."""

    surface = _find_unread_surface(page)
    if surface is None:
        raise RuntimeError("Unread surface was not found before row click.")

    _scroll_unread_list_to_start(surface)
    page.wait_for_timeout(400)

    bottom_passes = 0

    for _ in range(45):
        name_locator = _find_visible_unread_name(surface, unread_name)
        if name_locator is not None:
            if not _click_conversation_name(name_locator):
                raise RuntimeError(
                    f"Conversation row click failed for {unread_name!r}."
                )
            page.wait_for_timeout(CONVERSATION_SETTLE_MS)
            logger.info(
                (
                    "Opened matched conversation | unread_name=%s | "
                    "settle_ms=%s | url=%s"
                ),
                unread_name,
                CONVERSATION_SETTLE_MS,
                page.url,
            )
            return

        scroll_state = _scroll_unread_list(surface)
        if bool(scroll_state.get("atBottom")):
            bottom_passes += 1
        else:
            bottom_passes = 0

        if bottom_passes >= 2:
            break

        page.wait_for_timeout(400)

    raise RuntimeError(
        f"Matched conversation row was not found for {unread_name!r}."
    )


def _message_group_for_body(body: Locator) -> Locator | None:
    selectors = (
        (
            'xpath=ancestor::*['
            'contains(@class,"msg-s-message-group")][1]'
        ),
        (
            'xpath=ancestor::*['
            'contains(@class,"msg-s-event-listitem")][1]'
        ),
        'xpath=ancestor::li[1]',
    )

    for selector in selectors:
        try:
            group = body.locator(selector)
            if group.count() > 0:
                return group.first
        except Exception:
            continue

    return None


def _read_message_author(group: Locator | None) -> str:
    if group is None:
        return ""

    for selector in MESSAGE_AUTHOR_SELECTORS:
        try:
            candidates = group.locator(selector)
            for index in range(candidates.count()):
                candidate = candidates.nth(index)
                if not _is_visible(candidate):
                    continue
                value = " ".join(candidate.inner_text().split())
                if value:
                    return value
        except Exception:
            continue

    return ""


def _read_message_timestamp(group: Locator | None) -> str:
    if group is None:
        return ""

    date_value = ""
    date_xpath = (
        'xpath=preceding::*['
        'contains(@class,"msg-s-message-list__time-heading") or '
        'contains(@class,"msg-s-message-list__date-heading") or '
        'contains(@class,"msg-s-message-list__time-divider")'
        '][1]'
    )
    try:
        date_heading = group.locator(date_xpath)
        if date_heading.count() > 0:
            date_value = " ".join(
                date_heading.first.inner_text().split()
            )
    except Exception:
        date_value = ""

    selectors = (
        "time",
        ".msg-s-message-group__timestamp",
        ".msg-s-event-listitem__timestamp",
    )

    for selector in selectors:
        try:
            candidates = group.locator(selector)
            for index in range(candidates.count()):
                candidate = candidates.nth(index)
                for attribute in ("datetime", "title", "aria-label"):
                    attribute_value = str(
                        candidate.get_attribute(attribute) or ""
                    ).strip()
                    if attribute_value:
                        return attribute_value

                time_value = " ".join(candidate.inner_text().split())
                if time_value:
                    if date_value:
                        return f"{date_value} · {time_value}"
                    return time_value
        except Exception:
            continue

    return date_value


def _message_event_dom_key(body: Locator) -> str:
    """Return one stable key for nested selectors from the same message event."""

    try:
        return str(
            body.evaluate(
                """
                element => {
                    const eventNode =
                        element.closest('.msg-s-event-listitem') || element;
                    window.__outreachReplyEventKeys ||= new WeakMap();
                    window.__outreachReplyEventKeyCounter ||= 0;
                    if (!window.__outreachReplyEventKeys.has(eventNode)) {
                        window.__outreachReplyEventKeyCounter += 1;
                        window.__outreachReplyEventKeys.set(
                            eventNode,
                            `reply-event-${window.__outreachReplyEventKeyCounter}`
                        );
                    }
                    return window.__outreachReplyEventKeys.get(eventNode);
                }
                """
            )
            or ""
        ).strip()
    except Exception:
        return ""


def load_full_conversation(page: Page, unread_name: str) -> int:
    """Scroll the active thread upward until older messages stop loading."""

    surface = _find_unread_surface(page) or page
    scroll_container: Locator | None = None

    for selector in MESSAGE_SCROLL_CONTAINER_SELECTORS:
        try:
            candidates = surface.locator(selector)
            for index in range(candidates.count()):
                candidate = candidates.nth(index)
                if _is_visible(candidate):
                    scroll_container = candidate
                    logger.info(
                        "CONVERSATION SCROLL EVIDENCE | unread_name=%s | selector=%s",
                        unread_name,
                        selector,
                    )
                    break
        except Exception:
            continue
        if scroll_container is not None:
            break

    if scroll_container is None:
        logger.warning(
            "Conversation scroll container was not found | unread_name=%s",
            unread_name,
        )
        return 0

    stable_passes = 0
    previous_height = -1
    scroll_count = 0

    for _ in range(12):
        try:
            state_before = scroll_container.evaluate(
                """
                element => {
                    const result = {
                        height: element.scrollHeight,
                        top: element.scrollTop
                    };
                    element.scrollTo({top: 0, behavior: 'auto'});
                    element.dispatchEvent(new Event('scroll', {bubbles: true}));
                    return result;
                }
                """
            )
        except Exception:
            break

        scroll_count += 1
        page.wait_for_timeout(1_200)

        try:
            current_height = int(
                scroll_container.evaluate("element => element.scrollHeight")
                or 0
            )
        except Exception:
            current_height = 0

        if current_height == previous_height and int(
            state_before.get("top") or 0
        ) == 0:
            stable_passes += 1
        else:
            stable_passes = 0

        logger.info(
            (
                "CONVERSATION SCROLL | unread_name=%s | pass=%s | "
                "height_before=%s | height_after=%s | stable_passes=%s"
            ),
            unread_name,
            scroll_count,
            state_before.get("height"),
            current_height,
            stable_passes,
        )

        previous_height = current_height
        if stable_passes >= 2:
            break

    return scroll_count


def read_incoming_reply_messages(
    page: Page,
    *,
    unread_name: str,
    sent_message_text: str,
) -> tuple[list[dict], list[dict]]:
    """Read incoming bubble text only from the active matched thread."""

    surface = _find_unread_surface(page)
    if surface is None:
        surface = page

    body_locator = surface.locator(", ".join(MESSAGE_BODY_SELECTORS))
    expected_author = _normalize_name(unread_name)
    normalized_sent_text = " ".join(str(sent_message_text or "").split())
    events: list[dict] = []
    seen_dom_event_keys: set[str] = set()

    logger.info(
        "MESSAGE DOM EVIDENCE | unread_name=%s | selectors=%s | candidates=%s",
        unread_name,
        MESSAGE_BODY_SELECTORS,
        body_locator.count(),
    )

    for index in range(body_locator.count()):
        body = body_locator.nth(index)

        try:
            if not _is_visible(body):
                continue
            text_value = " ".join(body.inner_text().split())
        except Exception:
            continue

        if not text_value:
            continue

        dom_event_key = _message_event_dom_key(body)
        dom_message_key = (
            f"{dom_event_key}|{' '.join(text_value.casefold().split())}"
            if dom_event_key
            else ""
        )
        if dom_message_key and dom_message_key in seen_dom_event_keys:
            logger.debug(
                "Skipping duplicate nested message selector | dom_event_key=%s",
                dom_event_key,
            )
            continue
        if dom_message_key:
            seen_dom_event_keys.add(dom_message_key)

        group = _message_group_for_body(body)
        author = _read_message_author(group)
        normalized_author = _normalize_name(author)

        class_evidence = ""
        if group is not None:
            try:
                class_evidence = str(
                    group.get_attribute("class") or ""
                ).casefold()
            except Exception:
                class_evidence = ""

        is_own_message = (
            "--is-me" in class_evidence
            or "from-me" in class_evidence
            or (
                normalized_sent_text
                and text_value == normalized_sent_text
            )
        )
        is_incoming = (
            bool(normalized_author)
            and normalized_author == expected_author
            and not is_own_message
        )

        events.append(
            {
                "index": len(events),
                "author": author,
                "text": text_value,
                "timestamp": _read_message_timestamp(group),
                "is_own_message": is_own_message,
                "is_incoming": is_incoming,
            }
        )

    last_sent_index = -1
    for event in events:
        if event["is_own_message"]:
            last_sent_index = max(last_sent_index, int(event["index"]))

    replies = [
        event
        for event in events
        if event["is_incoming"] and int(event["index"]) > last_sent_index
    ]

    if not replies:
        incoming_events = [event for event in events if event["is_incoming"]]
        if incoming_events:
            replies = [incoming_events[-1]]

    logger.info(
        (
            "MESSAGE READ EVIDENCE | unread_name=%s | bubbles=%s | "
            "last_sent_index=%s | incoming_replies=%s"
        ),
        unread_name,
        len(events),
        last_sent_index,
        len(replies),
    )
    return replies, events


def _visible_exact_text(page: Page, text_value: str) -> Locator | None:
    candidates = (
        page.get_by_role("menuitem", name=text_value, exact=True),
        page.get_by_text(text_value, exact=True),
    )

    for locator in candidates:
        try:
            for index in range(locator.count()):
                candidate = locator.nth(index)
                if _is_visible(candidate):
                    return candidate
        except Exception:
            continue

    return None


def _find_overflow_beside_star(
    page: Page,
    unread_name: str,
) -> Locator:
    """Find the thread menu whose accessible label names this profile."""

    normalized_target = _normalize_name(unread_name)

    # Current LinkedIn DOM exposes the active-thread menu directly as:
    # button.msg-thread-actions__control.artdeco-dropdown__trigger
    # Its hidden accessible text starts with "Open the options list in your
    # conversation ...". Prefer that stable semantic evidence over position.
    for selector in THREAD_OVERFLOW_SELECTORS:
        try:
            candidates = page.locator(selector)
            for index in range(candidates.count()):
                candidate = candidates.nth(index)
                if not _is_visible(candidate):
                    continue

                hidden_text = " ".join(candidate.inner_text().split())
                normalized_hidden_text = _normalize_name(hidden_text)
                if normalized_target not in normalized_hidden_text:
                    logger.info(
                        (
                            "THREAD MENU SKIPPED | target=%s | "
                            "reason=accessible_name_does_not_match | "
                            "candidate_text=%s"
                        ),
                        unread_name,
                        hidden_text,
                    )
                    continue

                logger.info(
                    (
                        "THREAD MENU DOM EVIDENCE | strategy=direct-control | "
                        "target=%s | selector=%s | aria_expanded=%s | "
                        "hidden_text=%s"
                    ),
                    unread_name,
                    selector,
                    candidate.get_attribute("aria-expanded"),
                    hidden_text,
                )
                return candidate
        except Exception:
            continue

    for selector in THREAD_STAR_SELECTORS:
        try:
            stars = page.locator(selector)
            for index in range(stars.count()):
                star = stars.nth(index)
                if not _is_visible(star):
                    continue

                previous = star.locator(
                    "xpath=preceding-sibling::button[1]"
                )
                if previous.count() > 0 and _is_visible(previous.first):
                    hidden_text = " ".join(
                        previous.first.inner_text().split()
                    )
                    if normalized_target not in _normalize_name(hidden_text):
                        continue
                    logger.info(
                        (
                            "THREAD MENU DOM EVIDENCE | strategy=button-before-star | "
                            "target=%s | star_selector=%s | overflow_aria=%s | "
                            "overflow_title=%s | hidden_text=%s"
                        ),
                        unread_name,
                        selector,
                        previous.first.get_attribute("aria-label"),
                        previous.first.get_attribute("title"),
                        hidden_text,
                    )
                    return previous.first

                parent_buttons = star.locator("xpath=parent::*").locator(
                    ":scope > button"
                )
                for button_index in range(parent_buttons.count()):
                    button = parent_buttons.nth(button_index)
                    if not _is_visible(button):
                        continue
                    try:
                        icon_count = button.locator(
                            'svg[data-test-icon*="overflow"], '
                            'svg[data-test-icon*="ellipsis"]'
                        ).count()
                        aria_label = str(
                            button.get_attribute("aria-label") or ""
                        ).casefold()
                    except Exception:
                        continue
                    hidden_text = " ".join(button.inner_text().split())
                    target_matches = (
                        normalized_target in _normalize_name(hidden_text)
                    )
                    if target_matches and (
                        icon_count > 0 or "more" in aria_label
                    ):
                        logger.info(
                            (
                                "THREAD MENU DOM EVIDENCE | "
                                "strategy=star-parent-overflow | "
                                "target=%s | star_selector=%s | "
                                "overflow_aria=%s | hidden_text=%s"
                            ),
                            unread_name,
                            selector,
                            aria_label,
                            hidden_text,
                        )
                        return button
        except Exception:
            continue

    raise RuntimeError(
        "Active-thread overflow button was not found for "
        f"{unread_name!r}."
    )


def _open_thread_overflow_menu(page: Page, unread_name: str) -> None:
    overflow = _find_overflow_beside_star(page, unread_name)
    if not _click_locator(overflow):
        raise RuntimeError("Could not click thread overflow beside Star.")

    page.wait_for_timeout(THREAD_MENU_SETTLE_MS)

    for _ in range(30):
        if (
            _visible_exact_text(page, "Mark as unread") is not None
            or _visible_exact_text(page, "Mark as read") is not None
        ):
            return
        page.wait_for_timeout(100)

    raise RuntimeError("Thread overflow menu did not become visible.")


def mark_active_thread_as_unread(page: Page, unread_name: str) -> None:
    """Restore unread state and verify menu changes to Mark as read."""

    page.wait_for_timeout(BEFORE_THREAD_MENU_MS)
    _open_thread_overflow_menu(page, unread_name)

    mark_unread = _visible_exact_text(page, "Mark as unread")
    if mark_unread is not None:
        if not _click_locator(mark_unread):
            raise RuntimeError("Could not click exact Mark as unread item.")
        logger.info(
            "Clicked Mark as unread | unread_name=%s | settle_ms=%s",
            unread_name,
            MARK_UNREAD_SETTLE_MS,
        )
        page.wait_for_timeout(MARK_UNREAD_SETTLE_MS)
    else:
        already_unread = _visible_exact_text(page, "Mark as read")
        if already_unread is not None:
            page.keyboard.press("Escape")
            logger.info(
                "Conversation was already unread | unread_name=%s",
                unread_name,
            )
            return
        raise RuntimeError("Neither Mark as unread nor Mark as read was found.")

    verified = False
    for _ in range(5):
        page.wait_for_timeout(THREAD_MENU_SETTLE_MS)
        _open_thread_overflow_menu(page, unread_name)
        if _visible_exact_text(page, "Mark as read") is not None:
            verified = True
            page.keyboard.press("Escape")
            break
        page.keyboard.press("Escape")

    if not verified:
        raise RuntimeError(
            "Mark as unread click was not verified by Mark as read state."
        )

    logger.info(
        "MARKED AS UNREAD | unread_name=%s | verification=Mark as read visible",
        unread_name,
    )


def process_matched_conversations(
    page: Page,
    matched_profiles: list[dict],
    *,
    client,
) -> int:
    """Read matched replies and always attempt to restore unread state."""

    processed_count = 0

    for match in matched_profiles:
        unread_name = str(match.get("unread_name") or "").strip()
        sent_profile = dict(match.get("sent_profile") or {})
        conversation_opened = False

        try:
            open_matched_conversation(page, unread_name)
            conversation_opened = True

            load_full_conversation(page, unread_name)

            replies, conversation_events = read_incoming_reply_messages(
                page,
                unread_name=unread_name,
                sent_message_text=str(sent_profile.get("message_text") or ""),
            )

            if not replies:
                logger.warning(
                    (
                        "NO INCOMING MESSAGE BODY FOUND | unread_name=%s | "
                        "db_target_id=%s"
                    ),
                    unread_name,
                    sent_profile.get("id"),
                )
            else:
                for reply in replies:
                    logger.warning(
                        (
                            "REPLY MESSAGE CONTENT | sender=%s | message=%s | "
                            "message_time=%s | db_target_id=%s | "
                            "db_prospect_id=%s | match_reason=%s | "
                            "similarity=%.3f"
                        ),
                        unread_name,
                        reply.get("text"),
                        reply.get("timestamp"),
                        sent_profile.get("id"),
                        sent_profile.get("prospect_id"),
                        match.get("match_reason"),
                        float(match.get("similarity") or 0.0),
                    )

                latest_reply = replies[-1]
                try:
                    stored_reply = save_outreach_reply(
                        sent_target_id=str(sent_profile.get("id") or ""),
                        prospect_id=str(
                            sent_profile.get("prospect_id") or ""
                        ),
                        assigned_account_id=str(
                            sent_profile.get("assigned_account_id") or ""
                        ),
                        user_name=unread_name,
                        linkedin_url=str(
                            sent_profile.get("linkedin_url") or ""
                        ),
                        message_text=str(latest_reply.get("text") or ""),
                        linkedin_message_time=str(
                            latest_reply.get("timestamp") or ""
                        ),
                        conversation_messages=conversation_events,
                        match_reason=str(match.get("match_reason") or ""),
                        match_similarity=float(
                            match.get("similarity") or 0.0
                        ),
                        client=client,
                    )
                    logger.info(
                        (
                            "REPLY UPSERTED | reply_id=%s | "
                            "sent_target_id=%s | user_name=%s | "
                            "conversation_messages=%d"
                        ),
                        stored_reply.get("id"),
                        sent_profile.get("id"),
                        unread_name,
                        len(conversation_events),
                    )
                except Exception as exc:
                    logger.exception(
                        (
                            "REPLY STORE FAILED | sent_target_id=%s | "
                            "user_name=%s | error=%s"
                        ),
                        sent_profile.get("id"),
                        unread_name,
                        exc,
                    )

            processed_count += 1

        except Exception as exc:
            logger.exception(
                "Matched conversation processing failed | unread_name=%s | error=%s",
                unread_name,
                exc,
            )

        finally:
            if conversation_opened:
                try:
                    mark_active_thread_as_unread(page, unread_name)
                except Exception as exc:
                    logger.exception(
                        (
                            "Could not restore unread state | "
                            "unread_name=%s | error=%s"
                        ),
                        unread_name,
                        exc,
                    )

                page.wait_for_timeout(BETWEEN_CONVERSATIONS_MS)
                logger.info(
                    "Conversation cycle settled | unread_name=%s | wait_ms=%s",
                    unread_name,
                    BETWEEN_CONVERSATIONS_MS,
                )

    return processed_count


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
    """Read replies from matched sent targets, then restore unread state."""

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
        matched_profiles = log_sent_name_matches(
            unread_names=unread_names,
            sent_profiles=sent_profiles,
        )
        processed_count = process_matched_conversations(
            page,
            matched_profiles,
            client=client,
        )

        print("")
        print("Reply-check scan completed.")
        print(f"Unread names: {len(unread_names)}")
        print(f"Matched sent profiles: {len(matched_profiles)}")
        print(f"Matched conversations processed: {processed_count}")
        print("Reply contents and evidence were written to the worker log.")
        print("Reply-check worker finished. Closing the browser.")
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
