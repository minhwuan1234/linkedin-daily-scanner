from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.outreach_account_pool import OutreachAccount


CHECK_URL = "https://www.linkedin.com/feed/"

LOGIN_URL_PARTS = (
    "/login",
    "/uas/login",
    "/authwall",
)

CHECKPOINT_URL_PARTS = (
    "/checkpoint",
    "/challenge",
)

LOGIN_FORM_SELECTORS = (
    'input[name="session_key"]',
    'input[name="session_password"]',
)

LOGGED_IN_SELECTORS = (
    'a[href*="/feed/"]',
    'a[href*="/mynetwork/"]',
    'a[href*="/messaging/"]',
    'a[href*="/in/me/"]',
)


@dataclass(frozen=True)
class LinkedInSessionCheckResult:
    status: str
    current_url: str | None
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "current_url": self.current_url,
            "detail": self.detail,
        }


def _contains_any(value: str, parts: tuple[str, ...]) -> bool:
    lowered = str(value or "").lower()
    return any(part in lowered for part in parts)


def _has_visible(page, selector: str) -> bool:
    locator = page.locator(selector)

    for index in range(locator.count()):
        try:
            if locator.nth(index).is_visible():
                return True
        except Exception:
            continue

    return False


def check_outreach_account_session(
    account: OutreachAccount,
) -> LinkedInSessionCheckResult:
    """
    Open exactly one Outreach persistent browser profile and classify
    the LinkedIn session without entering credentials or changing data.

    Returns:
        logged_in
        logged_out
        checkpoint
        busy
        unknown
    """

    if not account.profile_directory.exists():
        return LinkedInSessionCheckResult(
            status="logged_out",
            current_url=None,
            detail="Browser profile directory does not exist yet.",
        )

    browser = account.create_browser_manager()

    try:
        try:
            browser.start()
        except Exception as exc:
            message = str(exc)
            lowered = message.lower()

            if (
                "opening in existing browser session" in lowered
                or "profile appears to be in use" in lowered
                or "singletonlock" in lowered
                or "processsingleton" in lowered
            ):
                return LinkedInSessionCheckResult(
                    status="busy",
                    current_url=None,
                    detail=(
                        "This browser profile is currently in use by another worker or browser."
                    ),
                )

            raise

        page = browser.ensure_page()

        try:
            page.goto(
                CHECK_URL,
                wait_until="domcontentloaded",
                timeout=30_000,
            )
        except PlaywrightTimeoutError:
            pass

        try:
            page.wait_for_timeout(900)
        except Exception:
            pass

        current_url = str(page.url or "").strip()

        if _contains_any(current_url, CHECKPOINT_URL_PARTS):
            return LinkedInSessionCheckResult(
                status="checkpoint",
                current_url=current_url,
                detail="LinkedIn requires verification or a checkpoint.",
            )

        if _contains_any(current_url, LOGIN_URL_PARTS):
            return LinkedInSessionCheckResult(
                status="logged_out",
                current_url=current_url,
                detail="LinkedIn redirected this profile to a login page.",
            )

        for selector in LOGIN_FORM_SELECTORS:
            if _has_visible(page, selector):
                return LinkedInSessionCheckResult(
                    status="logged_out",
                    current_url=current_url,
                    detail="LinkedIn login form is visible.",
                )

        cookies = browser.context.cookies()
        has_li_at = any(
            str(cookie.get("name") or "") == "li_at"
            and bool(str(cookie.get("value") or "").strip())
            for cookie in cookies
        )

        has_logged_in_ui = any(
            _has_visible(page, selector)
            for selector in LOGGED_IN_SELECTORS
        )

        if (
            "/feed" in current_url.lower()
            and has_li_at
        ) or has_logged_in_ui:
            return LinkedInSessionCheckResult(
                status="logged_in",
                current_url=current_url,
                detail="LinkedIn session is active.",
            )

        if has_li_at:
            return LinkedInSessionCheckResult(
                status="logged_in",
                current_url=current_url,
                detail="LinkedIn authentication cookie is present.",
            )

        return LinkedInSessionCheckResult(
            status="unknown",
            current_url=current_url or None,
            detail="Could not confidently classify the LinkedIn session.",
        )

    finally:
        try:
            browser.stop()
        except Exception:
            pass
