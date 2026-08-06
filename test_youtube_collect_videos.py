from app.youtube_browser import (
    YouTubeBrowserManager,
)
from app.youtube_scanner import (
    apply_this_year_filter,
    collect_search_videos,
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

        videos = collect_search_videos(
            page,
            max_results=40,
        )

        print("")
        print(
            f"Collected videos: {len(videos)}"
        )

        for video in videos:
            print(
                video["video_position"],
                video["video_title"],
                video["video_url"],
            )

        input(
            "Press Enter to close browser..."
        )

    finally:
        browser.stop()


if __name__ == "__main__":
    main()
