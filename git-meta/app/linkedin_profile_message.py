from __future__ import annotations

from playwright.sync_api import (
    Locator,
    Page,
)


def _visible_text(
    locator: Locator,
) -> str:
    try:
        if not locator.is_visible():
            return ""

        return (
            locator
            .inner_text()
            .strip()
        )

    except Exception:
        return ""


def _clean_profile_name(
    raw_text: str,
) -> str:
    text = " ".join(
        str(
            raw_text
            or ""
        ).split()
    ).strip()

    if not text:
        return ""

    # Reject obvious non-name UI labels.
    lowered = text.lower()

    rejected = {
        "message",
        "more",
        "connect",
        "follow",
        "pending",
        "contact info",
    }

    if lowered in rejected:
        return ""

    # Avoid accidentally taking long page sections.
    if len(text) > 120:
        return ""

    return text


def get_profile_name(
    page: Page,
) -> dict[str, str]:
    """
    STEP 3A — read LinkedIn profile name.

    The previous version was too narrow and could miss
    newer LinkedIn profile-header DOM.

    Strategy:
    1. try known semantic/header selectors;
    2. try visible heading elements inside <main>;
    3. choose the first short, name-like visible heading.

    No message is sent here.
    """

    selector_groups = (
        'div[data-testid="lazy-column"] h2',
        'main h1',
        'main h2',
        'main [role="heading"][aria-level="1"]',
        'main [role="heading"][aria-level="2"]',
    )

    seen: set[str] = set()

    for selector in selector_groups:
        candidates = page.locator(
            selector
        )

        for index in range(
            candidates.count()
        ):
            candidate = candidates.nth(
                index
            )

            text = _clean_profile_name(
                _visible_text(
                    candidate
                )
            )

            if not text:
                continue

            if text in seen:
                continue

            seen.add(
                text
            )

            first_name = (
                text
                .split()[0]
                .strip()
            )

            if not first_name:
                continue

            return {
                "full_name": text,
                "first_name": first_name,
            }

    # Last semantic fallback:
    # inspect visible headings in main, without relying on
    # hashed LinkedIn class names.
    headings = page.locator(
        'main [role="heading"], '
        'main h1, '
        'main h2, '
        'main h3'
    )

    for index in range(
        headings.count()
    ):
        candidate = headings.nth(
            index
        )

        text = _clean_profile_name(
            _visible_text(
                candidate
            )
        )

        if not text:
            continue

        words = text.split()

        # Names are usually compact. Skip very short UI tokens
        # and very long section headings.
        if not (
            1 <= len(words) <= 8
        ):
            continue

        first_name = words[0].strip()

        if not first_name:
            continue

        return {
            "full_name": text,
            "first_name": first_name,
        }

    raise RuntimeError(
        "Profile header name was not found."
    )
