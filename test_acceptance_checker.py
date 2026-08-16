from app.linkedin_acceptance_checker import (
    check_profile_acceptance,
)
from app.outreach_account_pool import (
    OutreachAccountPool,
)


ACCOUNT_ID = "outreach_account_03"
LINKEDIN_URL = "https://www.linkedin.com/in/minh-quân-851170229/"


def main() -> None:
    pool = OutreachAccountPool()

    account = pool.get_account(
        ACCOUNT_ID
    )

    print("")
    print("=" * 60)
    print("ACCEPTANCE CHECK TEST")
    print("=" * 60)
    print(
        "Account:",
        account.account_id,
        f"({account.display_name})",
    )
    print(
        "LinkedIn URL:",
        LINKEDIN_URL,
    )

    browser = (
        account.create_browser_manager()
    )

    try:
        browser.start()

        result = check_profile_acceptance(
            browser=browser,
            linkedin_url=LINKEDIN_URL,
        )

        print("")
        print("=" * 60)
        print("RESULT")
        print("=" * 60)
        print(
            "Status:",
            result.status,
        )
        print(
            "Message:",
            result.message,
        )
        print(
            "Final URL:",
            result.final_url,
        )

    finally:
        browser.stop()


if __name__ == "__main__":
    main()
