import json

from app.youtube_browser import YouTubeBrowserManager
from app.youtube_scanner import (
    apply_this_year_filter,
    collect_unique_channels_from_results,
    scan_channel_list,
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

        apply_this_year_filter(page)

        channels = collect_unique_channels_from_results(
            page,
            max_channels=3,
        )

        print("")
        print(f"Collected channels: {len(channels)}")

        results = scan_channel_list(
            browser=browser,
            channels=channels,
        )

        print("")
        print("==============================")
        print("CHANNEL 1 RAW JSON")
        print("==============================")

        if results:
            print(
                json.dumps(
                    results[0],
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )

        print("")
        print("==============================")
        print("CHANNEL SCAN RESULTS")
        print("==============================")

        for result in results:
            print("")
            print(
                "Position:",
                result["channel_position"],
            )
            print(
                "Name:",
                result["channel_name"],
            )
            print(
                "URL:",
                result["channel_url"],
            )
            print(
                "Subscribers:",
                result["subscriber_count_text"],
            )
            print(
                "Videos:",
                result["video_count_text"],
            )
            print("Description:")
            print(result["channel_description"])
            print("------------------------------")

        input("Press Enter to close browser...")

    finally:
        browser.stop()


if __name__ == "__main__":
    main()
