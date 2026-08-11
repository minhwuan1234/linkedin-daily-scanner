from __future__ import annotations

from app.linkedin_connect_action import (
    connect_profile,
)
from app.outreach_account_pool import (
    OutreachAccountPool,
)


ACCOUNT_ID = "outreach_account_01"

TEST_LINKEDIN_URL = (
    "https://www.linkedin.com/in/minh-quân-851170229/"
)


def main() -> None:
    pool = OutreachAccountPool()

    account = pool.get_account(
        ACCOUNT_ID
    )

    print("")
    print("=" * 60)
    print("OUTREACH CONNECT TEST")
    print("=" * 60)

    print(
        f"Account: {account.account_id}"
    )

    print(
        "Profile directory: "
        f"{account.profile_directory}"
    )

    print(
        f"Target: {TEST_LINKEDIN_URL}"
    )

    browser = (
        account.create_browser_manager()
    )

    try:
        browser.start()

        result = connect_profile(
            browser=browser,
            linkedin_url=(
                TEST_LINKEDIN_URL
            ),
        )

        print("")
        print("=" * 60)
        print("CONNECT RESULT")
        print("=" * 60)

        print(
            f"status: {result.status}"
        )

        print(
            f"linkedin_url: "
            f"{result.linkedin_url}"
        )

        print(
            f"final_url: "
            f"{result.final_url}"
        )

        print(
            f"message: "
            f"{result.message}"
        )

        print("")

        input(
            "Check browser, "
            "then press Enter to close..."
        )

    finally:
        browser.stop()


if __name__ == "__main__":
    main()
