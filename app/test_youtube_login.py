from __future__ import annotations

from app.youtube_browser import (
    YouTubeBrowserManager,
)


def main() -> None:
    browser = YouTubeBrowserManager()

    try:
        browser.start()

        page = browser.open_youtube_home()

        print("")
        print("==============================")
        print("YOUTUBE LOGIN TEST")
        print("==============================")
        print("")
        print(
            "Profile folder:",
            browser.settings.profile_directory,
        )
        print("")
        print(
            "1. Đăng nhập tài khoản Google/YouTube "
            "trong cửa sổ Chromium."
        )
        print(
            "2. Khi avatar tài khoản đã hiện ở góc phải, "
            "quay lại Terminal."
        )
        print(
            "3. Nhấn Enter để kiểm tra session."
        )
        print("")

        while True:
            command = input(
                "Nhấn Enter để kiểm tra, hoặc nhập q để thoát: "
            ).strip().lower()

            if command == "q":
                print(
                    "Đã thoát mà không xác nhận login."
                )
                break

            try:
                page.reload(
                    wait_until="domcontentloaded"
                )
                page.wait_for_timeout(
                    3_000
                )
            except Exception:
                pass

            is_logged_in = (
                browser.is_youtube_logged_in(
                    page=page
                )
            )

            print("")
            print("==============================")

            if is_logged_in:
                print("LOGIN STATUS: SUCCESS")
                print(
                    "YouTube session đã được lưu "
                    "trong browser profile."
                )
                print(
                    "Bây giờ có thể chạy lại:"
                )
                print(
                    "python3 "
                    "test_youtube_collect_channels.py"
                )
                print("==============================")
                break

            print("LOGIN STATUS: NOT DETECTED")
            print(
                "Chưa thấy avatar tài khoản."
            )
            print(
                "Hãy hoàn tất đăng nhập trong Chromium "
                "rồi kiểm tra lại."
            )
            print("==============================")
            print("")

    finally:
        print("")
        print(
            "Đang đóng Chromium và lưu browser profile..."
        )
        browser.stop()
        print("Đã đóng browser.")


if __name__ == "__main__":
    main()
