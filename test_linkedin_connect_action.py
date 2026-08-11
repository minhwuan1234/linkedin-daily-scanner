from app.outreach_account_pool import (
    OutreachAccountPool,
)
from app.linkedin_connect_action import (
    connect_profile,
)


TEST_LINKEDIN_URL = (
    "https://www.linkedin.com/in/minh-quân-851170229/"
)


def main() -> None:
    pool = OutreachAccountPool()

    account = pool.get_account(
        "outreach_account_01"
    )

    print("")
    print(
        f"Using account: {account.account_id}"
    )
    print(
        f"Profile dir: "
        f"{account.profile_directory}"
    )
    print(
        f"Target: {TEST_LINKEDIN_URL}"
    )
    print("")

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
        print("==============================")
        print("CONNECT RESULT")
        print("==============================")
        print(
            f"status: {result.status}"
        )
        print(
            f"linkedin_url: "
            f"{result.linkedin_url}"
        )
        print(
            f"final_url: {result.final_url}"
        )
        print(
            f"message: {result.message}"
        )
        print("")

        input(
            "Check browser, then press "
            "Enter to close..."
        )

    finally:
        browser.stop()


if __name__ == "__main__":
    main()
