from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from app.linkedin_browser import (
    LinkedInBrowserManager,
)
from app.profile_raw_scraper import (
    OUTPUT_DIR,
    scrape_profile_raw,
)
from app.profile_snapshot_store import (
    mark_source_scanned,
    save_profile_snapshot,
)
from app.settings import load_settings


def read_bool_env(
    key: str,
    *,
    default: bool,
) -> bool:
    """
    Đọc boolean từ environment variable.
    """
    raw_value = os.getenv(key)

    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()

    if normalized in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }:
        return True

    if normalized in {
        "0",
        "false",
        "no",
        "n",
        "off",
    }:
        return False

    raise ValueError(
        f"Invalid boolean environment variable "
        f"{key}={raw_value!r}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scrape raw LinkedIn profile data "
            "and save it to Supabase."
        )
    )

    parser.add_argument(
        "--source-id",
        type=int,
        default=None,
        help=(
            "Specific linkedin_sources ID "
            "to scrape."
        ),
    )

    browser_group = (
        parser.add_mutually_exclusive_group()
    )

    browser_group.add_argument(
        "--keep-browser-open",
        action="store_true",
        help=(
            "Keep the Chromium browser open after "
            "the scan. Press Enter or Ctrl+C to close."
        ),
    )

    browser_group.add_argument(
        "--close-browser",
        action="store_true",
        help=(
            "Close Chromium immediately after "
            "the scan is completed."
        ),
    )

    return parser.parse_args()


def resolve_keep_browser_open(
    args: argparse.Namespace,
) -> bool:
    """
    Xác định có giữ browser mở sau khi scan hay không.

    Thứ tự ưu tiên:
    1. CLI --keep-browser-open
    2. CLI --close-browser
    3. LINKEDIN_KEEP_BROWSER_OPEN trong .env
    """
    if args.keep_browser_open:
        return True

    if args.close_browser:
        return False

    return read_bool_env(
        "LINKEDIN_KEEP_BROWSER_OPEN",
        default=True,
    )


def save_result_to_json(
    result: dict[str, Any],
) -> Path:
    """
    Lưu toàn bộ kết quả raw vào thư mục output.
    """
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_id = int(
        result["source_id"]
    )

    output_path = Path(
        OUTPUT_DIR,
        f"profile_{source_id}.json",
    )

    output_path.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    return output_path


def print_scan_summary(
    *,
    result: dict[str, Any],
    snapshot_id: int,
    output_path: Path,
) -> None:
    """
    In kết quả scan ra Terminal.
    """
    source_id = result["source_id"]

    profile = result.get(
        "profile",
        {},
    )

    if not isinstance(profile, dict):
        profile = {}

    experience_raw_text = result.get(
        "experience_raw_text",
        "",
    )

    if not isinstance(
        experience_raw_text,
        str,
    ):
        experience_raw_text = str(
            experience_raw_text or ""
        )

    recent_post_captions = result.get(
        "recent_post_captions",
        [],
    )

    if not isinstance(
        recent_post_captions,
        list,
    ):
        recent_post_captions = []

    errors = result.get(
        "errors",
        [],
    )

    if not isinstance(errors, list):
        errors = []

    print("")
    print(
        "LinkedIn raw profile scrape completed."
    )
    print(
        f"Source ID: {source_id}"
    )
    print(
        f"Snapshot ID: {snapshot_id}"
    )
    print(
        f"Name: {profile.get('name', '')}"
    )
    print(
        "Headline: "
        f"{profile.get('headline', '')}"
    )
    print(
        "Location: "
        f"{profile.get('location', '')}"
    )
    print(
        "About length: "
        f"{len(profile.get('about_text', '') or '')}"
    )
    print(
        "Experience raw length: "
        f"{len(experience_raw_text)}"
    )
    print(
        "Post captions found: "
        f"{len(recent_post_captions)}"
    )
    print(
        f"Section errors: {len(errors)}"
    )

    if recent_post_captions:
        print("")
        print("Recent post captions:")

        for index, caption in enumerate(
            recent_post_captions,
            start=1,
        ):
            cleaned_caption = str(
                caption or ""
            ).strip()

            preview = cleaned_caption.replace(
                "\n",
                " ",
            )

            if len(preview) > 180:
                preview = (
                    preview[:177] + "..."
                )

            print(
                f"  {index}. {preview}"
            )

    if errors:
        print("")
        print("Section errors:")

        for error in errors:
            if isinstance(error, dict):
                section = (
                    error.get("section")
                    or error.get("stage")
                    or "unknown"
                )

                message = error.get(
                    "message",
                    "",
                )

                print(
                    f"  - {section}: {message}"
                )
            else:
                print(
                    f"  - {error}"
                )

    print("")
    print(
        f"Output: {output_path.resolve()}"
    )


def wait_before_closing_browser() -> None:
    """
    Giữ process và browser sống sau khi scan.

    Đây là chế độ test thủ công.
    Worker sau này sẽ giữ browser bằng vòng polling,
    không sử dụng input().
    """
    print("")
    print(
        "Browser is still open."
    )
    print(
        "Press Enter to close it, "
        "or press Ctrl+C."
    )

    try:
        input()
    except (
        KeyboardInterrupt,
        EOFError,
    ):
        print("")


def main() -> int:
    browser: LinkedInBrowserManager | None = None

    try:
        args = parse_args()
        settings = load_settings()

        keep_browser_open = (
            resolve_keep_browser_open(args)
        )

        browser = LinkedInBrowserManager()
        browser.start()

        result = scrape_profile_raw(
            settings=settings,
            source_id=args.source_id,
            browser=browser,
        )

        output_path = save_result_to_json(
            result
        )

        snapshot_id = save_profile_snapshot(
            settings=settings,
            result=result,
        )

        mark_source_scanned(
            settings=settings,
            source_id=int(
                result["source_id"]
            ),
            scanned_at=str(
                result["scraped_at"]
            ),
        )

        print_scan_summary(
            result=result,
            snapshot_id=snapshot_id,
            output_path=output_path,
        )

        if keep_browser_open:
            wait_before_closing_browser()

        return 0

    except Exception as exc:
        print(
            "LinkedIn raw profile scrape failed: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )

        return 1

    finally:
        if browser is not None:
            browser.stop()


if __name__ == "__main__":
    raise SystemExit(main())
