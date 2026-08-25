from pathlib import Path

from playwright.sync_api import sync_playwright


ACCOUNT_ID = "outreach_account_05"

PROFILE_DIR = (
    Path("outreach_browser_profiles")
    / ACCOUNT_ID
).resolve()


def main() -> None:
    PROFILE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        f"Opening browser for: {ACCOUNT_ID}"
    )
    print(
        f"Profile directory: {PROFILE_DIR}"
    )

    with sync_playwright() as playwright:
        context = (
            playwright.chromium
            .launch_persistent_context(
                user_data_dir=str(PROFILE_DIR),
                headless=False,
            )
        )

        page = (
            context.pages[0]
            if context.pages
            else context.new_page()
        )

        page.goto(
            "https://www.linkedin.com/",
            wait_until="domcontentloaded",
        )

        print("")
        print(
            "Login LinkedIn manually."
        )
        print(
            "When login is complete, "
            "return to Terminal and press Enter."
        )

        input()

        context.close()

    print("")
    print(
        f"Session saved for {ACCOUNT_ID}"
    )


if __name__ == "__main__":
    main()
