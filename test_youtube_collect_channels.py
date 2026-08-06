from app.youtube_browser import (
    YouTubeBrowserManager,
)
from app.youtube_scanner import (
    apply_this_year_filter,
    collect_unique_channels_from_results,
    search_youtube,
)


def main() -> None:
    browser = YouTubeBrowserManager()

    try:
        browser.start()

        page = search_youtube(
            browser=browser,
            keyword="cardiology 101",
        )

        apply_this_year_filter(
            page
        )

        channels = (
            collect_unique_channels_from_results(
                page,
                max_channels=3,
            )
        )

        print("")
        print(
            f"Collected channels: {len(channels)}"
        )

        for channel in channels:
            print("")
            print(
                "Position:",
                channel["channel_position"],
            )
            print(
                "Name:",
                channel["channel_name"],
            )
            print(
                "URL:",
                channel["channel_url"],
            )

        input(
            "Press Enter to close browser..."
        )

    finally:
        browser.stop()


if __name__ == "__main__":
    main()
