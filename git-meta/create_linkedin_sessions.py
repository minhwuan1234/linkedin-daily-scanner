from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import (
    BrowserContext,
    Playwright,
    sync_playwright,
)


ACCOUNT_IDS = (
    "account_01",
    "account_02",
    "account_03",
    "account_04",
    "account_05",
)

PROFILE_ROOT = Path(
    "linkedin_browser_profiles"
)

LINKEDIN_LOGIN_URL = (
    "https://www.linkedin.com/login"
)

LINKEDIN_FEED_URL = (
    "https://www.linkedin.com/feed/"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create persistent LinkedIn browser "
            "sessions for scanner accounts."
        )
    )

    parser.add_argument(
        "--account",
        choices=ACCOUNT_IDS,
        default=None,
        help=(
            "Set up only one account. "
            "If omitted, all five accounts "
            "will be opened one by one."
        ),
    )

    return parser.parse_args()


def get_account_profile_directory(
    account_id: str,
) -> Path:
    return (
        PROFILE_ROOT
        / account_id
    ).resolve()


def launch_account_context(
    playwright: Playwright,
    *,
    account_id: str,
) -> BrowserContext:
    profile_directory = (
        get_account_profile_directory(
            account_id
        )
    )

    profile_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("")
    print("=" * 70)
    print(
        f"Opening LinkedIn session for "
        f"{account_id}"
    )
    print(
        f"Profile directory: "
        f"{profile_directory}"
    )

    context = (
        playwright.chromium
        .launch_persistent_context(
            user_data_dir=str(
                profile_directory
            ),
            headless=False,
            viewport={
                "width": 1440,
                "height": 1000,
            },
            locale="en-US",
            timezone_id=(
                "Asia/Ho_Chi_Minh"
            ),
            args=[
                "--no-default-browser-check",
                "--disable-popup-blocking",
            ],
        )
    )

    return context


def setup_account_session(
    playwright: Playwright,
    *,
    account_id: str,
) -> None:
    context = launch_account_context(
        playwright,
        account_id=account_id,
    )

    page = (
        context.pages[0]
        if context.pages
        else context.new_page()
    )

    try:
        page.goto(
            LINKEDIN_FEED_URL,
            wait_until="domcontentloaded",
            timeout=60_000,
        )

        print("")
        print(
            f"Browser opened for {account_id}."
        )
        print(
            "Log in to the correct LinkedIn "
            "account in this browser."
        )
        print(
            "After the LinkedIn feed is visible, "
            "return to Terminal."
        )
        print("")
        print(
            "Press Enter to save this session "
            "and continue."
        )

        input()

        current_url = (
            page.url or ""
        ).lower()

        blocked_parts = (
            "/login",
            "/checkpoint",
            "/authwall",
            "/challenge",
        )

        if any(
            part in current_url
            for part in blocked_parts
        ):
            print("")
            print(
                f"WARNING: {account_id} still "
                "appears to require login or "
                "verification."
            )
            print(
                f"Current URL: {page.url}"
            )
        else:
            print("")
            print(
                f"Session saved successfully "
                f"for {account_id}."
            )
            print(
                f"Current URL: {page.url}"
            )

    finally:
        context.close()


def main() -> int:
    try:
        args = parse_args()

        accounts = (
            (args.account,)
            if args.account
            else ACCOUNT_IDS
        )

        PROFILE_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )

        with sync_playwright() as playwright:
            for account_id in accounts:
                setup_account_session(
                    playwright,
                    account_id=account_id,
                )

        print("")
        print("=" * 70)
        print(
            "LinkedIn session setup completed."
        )

        for account_id in accounts:
            print(
                f"- {account_id}: "
                f"{get_account_profile_directory(account_id)}"
            )

        return 0

    except KeyboardInterrupt:
        print("")
        print(
            "Session setup cancelled."
        )

        return 130

    except Exception as exc:
        print(
            "Could not create LinkedIn sessions: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
