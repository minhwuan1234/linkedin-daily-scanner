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


def get_profile_name(
    page: Page,
) -> dict[str, str]:
    """
    STEP 3A — read the profile name.

    Start from the selector used by the old
    linkedin-auto-mass-messeages repo:

        div[data-testid="lazy-column"] h2

    Keep the behavior simple for now:
    - wait for visible name;
    - return full_name;
    - first_name = first token.

    No message is sent here.
    """

    selectors = (
        'div[data-testid="lazy-column"] h2',
        'main h1',
    )

    for selector in selectors:
        candidates = page.locator(
            selector
        )

        for index in range(
            candidates.count()
        ):
            candidate = candidates.nth(
                index
            )

            text = _visible_text(
                candidate
            )

            if not text:
                continue

            full_name = text

            first_name = (
                full_name
                .split()[0]
                .strip()
            )

            if not first_name:
                continue

            return {
                "full_name": full_name,
                "first_name": first_name,
            }

    raise RuntimeError(
        "Profile header name was not found."
    )
