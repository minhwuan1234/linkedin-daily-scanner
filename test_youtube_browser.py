from app.youtube_browser import (
    YouTubeBrowserManager,
)


browser = YouTubeBrowserManager()

try:
    browser.start()

    page = browser.open_start_page()

    print("Browser opened successfully")
    print("Current URL:", page.url)
    print(
        "Profile directory:",
        browser.settings.profile_directory,
    )

    input(
        "Press Enter to close browser..."
    )

finally:
    browser.stop()
