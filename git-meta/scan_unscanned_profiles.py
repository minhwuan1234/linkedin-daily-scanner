from __future__ import annotations

import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

from app.linkedin_browser import (
    LinkedInBrowserManager,
    LinkedInSessionError,
)
from app.linkedin_scanner import (
    create_supabase_client,
)
from app.profile_raw_scraper import (
    OUTPUT_DIR,
    scrape_profile_raw,
)
from app.profile_snapshot_store import (
    mark_source_scanned,
    save_profile_snapshot,
)
from app.settings import Settings, load_settings


SOURCE_TABLE = "linkedin_sources"

DEFAULT_BATCH_SIZE = 10
MAX_BATCH_SIZE = 10

DEFAULT_MIN_DELAY_SECONDS = 8
DEFAULT_MAX_DELAY_SECONDS = 20


def read_int_env(
    key: str,
    *,
    default: int,
    minimum: int,
    maximum: int | None = None,
) -> int:
    """
    Đọc integer từ environment variable.

    Có validate để tránh cấu hình sai làm worker chạy
    quá nhiều source hoặc delay âm.
    """
    raw_value = os.getenv(key)

    if raw_value is None:
        value = default
    else:
        try:
            value = int(raw_value.strip())
        except ValueError as exc:
            raise ValueError(
                f"Invalid integer environment variable "
                f"{key}={raw_value!r}"
            ) from exc

    if value < minimum:
        raise ValueError(
            f"{key} must be >= {minimum}, "
            f"received {value}"
        )

    if maximum is not None and value > maximum:
        raise ValueError(
            f"{key} must be <= {maximum}, "
            f"received {value}"
        )

    return value


def get_batch_size() -> int:
    """
    Batch scanner được chặn cứng tối đa 10 source.

    Kể cả người dùng cấu hình lớn hơn 10 trong .env,
    chương trình sẽ báo lỗi thay vì chạy vượt gateway.
    """
    return read_int_env(
        "LINKEDIN_SCAN_BATCH_SIZE",
        default=DEFAULT_BATCH_SIZE,
        minimum=1,
        maximum=MAX_BATCH_SIZE,
    )


def get_scan_delay_range() -> tuple[int, int]:
    """
    Đọc khoảng nghỉ giữa hai profile.

    Delay giúp tránh việc scanner điều hướng quá dồn dập.
    """
    minimum_delay = read_int_env(
        "LINKEDIN_MIN_DELAY_SECONDS",
        default=DEFAULT_MIN_DELAY_SECONDS,
        minimum=0,
        maximum=300,
    )

    maximum_delay = read_int_env(
        "LINKEDIN_MAX_DELAY_SECONDS",
        default=DEFAULT_MAX_DELAY_SECONDS,
        minimum=0,
        maximum=300,
    )

    if maximum_delay < minimum_delay:
        raise ValueError(
            "LINKEDIN_MAX_DELAY_SECONDS must be "
            "greater than or equal to "
            "LINKEDIN_MIN_DELAY_SECONDS"
        )

    return minimum_delay, maximum_delay


def get_unscanned_sources(
    settings: Settings,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """
    Lấy các LinkedIn source đang enabled và chưa scan.

    Hàm vẫn giữ tương thích với cách gọi cũ:

        get_unscanned_sources(settings)

    Nếu không truyền limit, mặc định dùng gateway tối đa 10.
    """
    batch_limit = (
        get_batch_size()
        if limit is None
        else int(limit)
    )

    if batch_limit < 1:
        raise ValueError(
            "Source batch limit must be at least 1"
        )

    if batch_limit > MAX_BATCH_SIZE:
        raise ValueError(
            f"Source batch limit cannot exceed "
            f"{MAX_BATCH_SIZE}"
        )

    client = create_supabase_client(
        settings
    )

    response = (
        client
        .table(SOURCE_TABLE)
        .select(
            "id,name,linkedin_url,"
            "source_type,last_scanned_at"
        )
        .eq(
            "enabled",
            True,
        )
        .is_(
            "last_scanned_at",
            "null",
        )
        .order(
            "id",
            desc=False,
        )
        .limit(
            batch_limit
        )
        .execute()
    )

    rows = list(
        response.data or []
    )

    return rows[:batch_limit]


def save_local_output(
    result: dict[str, Any],
) -> Path:
    """
    Lưu kết quả raw local trước khi kết thúc source.

    File local giúp debug khi Supabase hoặc mapping gặp lỗi.
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


def get_result_post_count(
    result: dict[str, Any],
) -> int:
    """
    Lấy số caption tìm được mà không giả định kiểu dữ liệu.
    """
    captions = result.get(
        "recent_post_captions",
        [],
    )

    if not isinstance(captions, list):
        return 0

    return len(captions)


def print_source_result(
    *,
    source_id: int,
    result: dict[str, Any],
    snapshot_id: int,
    output_path: Path,
) -> None:
    profile = result.get(
        "profile",
        {},
    )

    if not isinstance(profile, dict):
        profile = {}

    errors = result.get(
        "errors",
        [],
    )

    if not isinstance(errors, list):
        errors = []

    print(
        f"Completed source {source_id}."
    )
    print(
        f"Snapshot ID: {snapshot_id}"
    )
    print(
        f"Name: {profile.get('name', '')}"
    )
    print(
        "Post captions found: "
        f"{get_result_post_count(result)}"
    )
    print(
        f"Section errors: {len(errors)}"
    )
    print(
        f"Output: {output_path.resolve()}"
    )

    if errors:
        print("Section warnings:")

        for error in errors:
            if isinstance(error, dict):
                section = (
                    error.get("section")
                    or error.get("stage")
                    or "unknown"
                )

                message = str(
                    error.get("message", "")
                )

                print(
                    f"  - {section}: {message}"
                )
            else:
                print(
                    f"  - {error}"
                )


def wait_between_sources(
    *,
    minimum_seconds: int,
    maximum_seconds: int,
    is_last_source: bool,
) -> None:
    """
    Nghỉ giữa hai source.

    Không delay sau source cuối cùng.
    """
    if is_last_source:
        return

    if maximum_seconds <= 0:
        return

    delay_seconds = random.randint(
        minimum_seconds,
        maximum_seconds,
    )

    print("")
    print(
        f"Waiting {delay_seconds} seconds "
        "before the next profile..."
    )

    time.sleep(
        delay_seconds
    )


def main() -> int:
    browser: LinkedInBrowserManager | None = None

    try:
        settings = load_settings()

        batch_size = get_batch_size()

        (
            minimum_delay_seconds,
            maximum_delay_seconds,
        ) = get_scan_delay_range()

        sources = get_unscanned_sources(
            settings=settings,
            limit=batch_size,
        )

        total = len(sources)

        if total == 0:
            print("")
            print(
                "No enabled unscanned LinkedIn "
                "sources found."
            )

            return 0

        print("")
        print(
            f"Found {total} unscanned profiles."
        )
        print(
            "Batch gateway: "
            f"{batch_size}/{MAX_BATCH_SIZE}"
        )
        print(
            "Browser mode: one persistent "
            "browser for the entire batch."
        )

        browser = LinkedInBrowserManager()
        browser.start()

        success_count = 0
        failed_count = 0
        batch_aborted = False

        for index, source in enumerate(
            sources,
            start=1,
        ):
            source_id = int(
                source["id"]
            )

            linkedin_url = str(
                source.get(
                    "linkedin_url",
                    "",
                )
                or ""
            ).strip()

            print("")
            print(
                "=" * 60
            )
            print(
                f"[{index}/{total}] "
                f"Scanning source {source_id}"
            )
            print(
                f"URL: {linkedin_url}"
            )

            if not linkedin_url:
                failed_count += 1

                print(
                    f"Failed source {source_id}: "
                    "linkedin_url is empty.",
                    file=sys.stderr,
                )

                continue

            try:
                result = scrape_profile_raw(
                    settings=settings,
                    source_id=source_id,
                    browser=browser,
                )

                result_source_id = int(
                    result["source_id"]
                )

                if result_source_id != source_id:
                    raise RuntimeError(
                        "Scraper returned a different "
                        "source_id. "
                        f"Expected {source_id}, "
                        f"received {result_source_id}."
                    )

                output_path = save_local_output(
                    result
                )

                snapshot_id = save_profile_snapshot(
                    settings=settings,
                    result=result,
                )

                # Chỉ mark scanned sau khi snapshot đã
                # được ghi thành công vào Supabase.
                mark_source_scanned(
                    settings=settings,
                    source_id=source_id,
                    scanned_at=str(
                        result["scraped_at"]
                    ),
                )

                success_count += 1

                print_source_result(
                    source_id=source_id,
                    result=result,
                    snapshot_id=snapshot_id,
                    output_path=output_path,
                )

            except LinkedInSessionError as exc:
                failed_count += 1
                batch_aborted = True

                print(
                    "",
                    file=sys.stderr,
                )
                print(
                    "LinkedIn session requires "
                    "manual attention.",
                    file=sys.stderr,
                )
                print(
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )
                print(
                    "Batch stopped to avoid sending "
                    "more requests while login or "
                    "verification is required.",
                    file=sys.stderr,
                )

                break

            except Exception as exc:
                failed_count += 1

                print(
                    f"Failed source {source_id}: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )

                # Không mark source scanned.
                # Source này vẫn còn last_scanned_at = null
                # để có thể retry ở batch tiếp theo.

            is_last_source = (
                index >= total
                or batch_aborted
            )

            wait_between_sources(
                minimum_seconds=(
                    minimum_delay_seconds
                ),
                maximum_seconds=(
                    maximum_delay_seconds
                ),
                is_last_source=is_last_source,
            )

        print("")
        print(
            "=" * 60
        )
        print(
            "Batch scan completed."
        )
        print(
            f"Batch limit: {batch_size}"
        )
        print(
            f"Loaded: {total}"
        )
        print(
            f"Success: {success_count}"
        )
        print(
            f"Failed: {failed_count}"
        )
        print(
            f"Aborted: {batch_aborted}"
        )

        if batch_aborted:
            return 2

        return (
            0
            if failed_count == 0
            else 1
        )

    except Exception as exc:
        print(
            "LinkedIn batch scan failed: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )

        return 1

    finally:
        if browser is not None:
            browser.stop()


if __name__ == "__main__":
    raise SystemExit(main())
