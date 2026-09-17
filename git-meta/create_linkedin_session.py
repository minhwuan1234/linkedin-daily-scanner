from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


PROFILE_DIR = Path("linkedin_browser_profile")


def main() -> None:
    PROFILE_DIR.mkdir(exist_ok=True)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={
                "width": 1440,
                "height": 1000,
            },
            locale="en-US",
            timezone_id="Asia/Ho_Chi_Minh",
        )

        page = (
            context.pages[0]
            if context.pages
            else context.new_page()
        )

        try:
            page.goto(
                "https://www.linkedin.com/login",
                wait_until="domcontentloaded",
                timeout=60_000,
            )

            print("")
            print("Đăng nhập LinkedIn trong cửa sổ trình duyệt.")
            print("Accept cookies và hoàn thành OTP nếu có.")
            print("Mở thử một profile LinkedIn.")
            print("")

            input(
                "Khi profile đã mở bình thường, "
                "quay lại PowerShell và nhấn Enter..."
            )

            current_url = page.url

            blocked_paths = (
                "/login",
                "/authwall",
                "/checkpoint",
            )

            if any(
                path in current_url
                for path in blocked_paths
            ):
                raise RuntimeError(
                    "Session chưa hoạt động. "
                    f"Current URL: {current_url}"
                )

            print("")
            print("Đã lưu browser profile tại:")
            print(PROFILE_DIR.resolve())

        finally:
            context.close()


if __name__ == "__main__":
    main()
