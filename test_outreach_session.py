from pathlib import Path

from playwright.sync_api import sync_playwright


ACCOUNT_ID = "outreach_account_01"

PROFILE_DIR = (
    Path("outreach_browser_profiles")
    / ACCOUNT_ID
).resolve()


def main() -> None:
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
            "https://www.linkedin.com/feed/",
            wait_until="domcontentloaded",
        )

        page.wait_for_timeout(3000)

        print("")
        print("FINAL URL:")
        print(page.url)
        print("")

        input(
            "Check browser. "
            "If already logged in, press Enter..."
        )

        context.close()


if __name__ == "__main__":
    main()
