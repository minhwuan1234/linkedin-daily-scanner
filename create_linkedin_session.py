from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


OUTPUT_FILE = Path("linkedin_storage_state.json")


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=False,
        )

        context = browser.new_context(
            viewport={
                "width": 1440,
                "height": 1000,
            },
            locale="en-US",
        )

        page = context.new_page()

        try:
            page.goto(
                "https://www.linkedin.com/login",
                wait_until="domcontentloaded",
                timeout=60_000,
            )

            print("")
            print(
                "Hãy đăng nhập LinkedIn trong cửa sổ trình duyệt."
            )
            print(
                "Hoàn thành OTP/CAPTCHA nếu LinkedIn yêu cầu."
            )
            print("")

            input(
                "Khi đã vào được trang chủ LinkedIn, "
                "quay lại terminal và nhấn Enter..."
            )

            page.wait_for_timeout(3_000)

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
                    "LinkedIn session chưa đăng nhập "
                    "thành công. "
                    f"Current URL: {current_url}"
                )

            context.storage_state(
                path=str(OUTPUT_FILE),
                indexed_db=True,
            )

            print("")
            print(
                "Đã tạo session tại:"
            )
            print(OUTPUT_FILE.resolve())
            print("")
            print(
                "Không upload file này lên GitHub."
            )

        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    main()
