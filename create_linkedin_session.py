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

        page.goto(
            "https://www.linkedin.com/login",
            wait_until="domcontentloaded",
        )

        print("")
        print("Hãy đăng nhập LinkedIn trong cửa sổ trình duyệt.")
        print("Hoàn thành OTP/CAPTCHA nếu LinkedIn yêu cầu.")
        print("")
        input(
            "Khi đã vào được trang chủ LinkedIn, "
            "quay lại terminal và nhấn Enter..."
        )

        page.wait_for_timeout(3_000)

current_url = page.url

if (
    "/login" in current_url
    or "/authwall" in current_url
    or "/checkpoint" in current_url
):
    raise RuntimeError(
        f"LinkedIn session chưa đăng nhập thành công. "
        f"Current URL: {current_url}"
    )

        if "/login" in page.url or "/authwall" in page.url:
            raise RuntimeError(
                "LinkedIn session chưa đăng nhập thành công."
            )

        context.storage_state(
            path=str(OUTPUT_FILE),
            indexed_db=True,
        )

        print("")
        print(
            f"Đã tạo session tại: {OUTPUT_FILE.resolve()}"
        )
        print("Không upload file này lên GitHub.")

        context.close()
        browser.close()


if __name__ == "__main__":
    main()
