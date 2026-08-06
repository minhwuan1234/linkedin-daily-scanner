from app.youtube_browser import (
    YouTubeBrowserManager,
)
from app.youtube_scanner import (
    search_youtube,
)


def main() -> None:
    browser = YouTubeBrowserManager()

    try:
        browser.start()

        page = search_youtube(
            browser=browser,
            keyword="AI automation",
        )

        print("")
        print("YouTube search opened.")
        print(f"Current URL: {page.url}")
        print(f"Page title: {page.title()}")

        input(
            "Press Enter to close browser..."
        )

    finally:
        browser.stop()


if __name__ == "__main__":
    main()
