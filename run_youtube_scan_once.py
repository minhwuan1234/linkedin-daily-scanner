from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any

from app.linkedin_scanner import (
    create_supabase_client,
)
from app.settings import load_settings
from app.youtube_browser import (
    YouTubeBrowserManager,
)
from app.youtube_result_store import (
    save_channel_results,
)
from app.youtube_scanner import (
    apply_this_year_filter,
    collect_unique_channels_from_results,
    scan_channel_list,
    search_youtube,
)


JOB_TABLE = "youtube_scan_jobs"
WORKER_ID = "youtube-scan-once"


def utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def parse_filters(
    raw_value: str,
) -> dict[str, Any]:
    cleaned = str(
        raw_value or ""
    ).strip()

    if not cleaned:
        return {}

    parsed = json.loads(
        cleaned
    )

    if not isinstance(
        parsed,
        dict,
    ):
        raise ValueError(
            "--filters must be a JSON object."
        )

    return parsed


def create_processing_job(
    *,
    keyword: str,
    max_results: int,
    filters: dict[str, Any],
) -> tuple[Any, dict[str, Any]]:
    settings = load_settings()

    client = create_supabase_client(
        settings
    )

    now = utc_now_iso()

    payload = {
        "keyword": keyword,
        "status": "processing",
        "current_stage": "starting",
        "progress_percent": 5,
        "max_results": max_results,
        "filters": filters,
        "retry_count": 0,
        "assigned_worker_id": WORKER_ID,
        "processing_started_at": now,
        "processing_heartbeat_at": now,
        "updated_at": now,
        "last_error": None,
    }

    response = (
        client
        .table(JOB_TABLE)
        .insert(
            payload
        )
        .execute()
    )

    rows = list(
        response.data or []
    )

    if not rows:
        raise RuntimeError(
            "Supabase did not return the created job."
        )

    return client, dict(
        rows[0]
    )


def update_job(
    client: Any,
    *,
    job_id: str,
    stage: str,
    progress_percent: int,
) -> None:
    now = utc_now_iso()

    response = (
        client
        .table(JOB_TABLE)
        .update(
            {
                "current_stage": stage,
                "progress_percent": max(
                    0,
                    min(
                        100,
                        int(progress_percent),
                    ),
                ),
                "processing_heartbeat_at": now,
                "updated_at": now,
            }
        )
        .eq(
            "id",
            job_id,
        )
        .execute()
    )

    if not list(
        response.data or []
    ):
        raise RuntimeError(
            f"Could not update job stage: {stage}"
        )


def complete_job(
    client: Any,
    *,
    job_id: str,
    result_count: int,
) -> None:
    now = utc_now_iso()

    response = (
        client
        .table(JOB_TABLE)
        .update(
            {
                "status": "completed",
                "current_stage": "completed",
                "progress_percent": 100,
                "result_count": max(
                    0,
                    int(result_count),
                ),
                "processing_heartbeat_at": now,
                "completed_at": now,
                "updated_at": now,
                "last_error": None,
            }
        )
        .eq(
            "id",
            job_id,
        )
        .execute()
    )

    if not list(
        response.data or []
    ):
        raise RuntimeError(
            "Could not complete YouTube job."
        )


def fail_job(
    client: Any,
    *,
    job_id: str,
    error_message: str,
) -> None:
    now = utc_now_iso()

    (
        client
        .table(JOB_TABLE)
        .update(
            {
                "status": "failed",
                "current_stage": "failed",
                "progress_percent": 100,
                "processing_heartbeat_at": now,
                "completed_at": now,
                "updated_at": now,
                "last_error": str(
                    error_message
                )[:4000],
            }
        )
        .eq(
            "id",
            job_id,
        )
        .execute()
    )


def run_scan_once(
    *,
    keyword: str,
    max_results: int,
    filters: dict[str, Any],
) -> int:
    client, job = create_processing_job(
        keyword=keyword,
        max_results=max_results,
        filters=filters,
    )

    job_id = str(
        job.get(
            "id",
            "",
        )
    ).strip()

    if not job_id:
        raise RuntimeError(
            "Created job is missing id."
        )

    print("")
    print("==============================")
    print("YOUTUBE SCAN ONCE")
    print("==============================")
    print(f"Job ID: {job_id}")
    print(f"Keyword: {keyword}")
    print(f"Max results: {max_results}")

    browser = YouTubeBrowserManager()

    try:
        browser.start()

        update_job(
            client,
            job_id=job_id,
            stage="searching",
            progress_percent=15,
        )

        page = search_youtube(
            browser=browser,
            keyword=keyword,
        )

        apply_this_year_filter(
            page
        )

        update_job(
            client,
            job_id=job_id,
            stage="collecting_channels",
            progress_percent=35,
        )

        channels = (
            collect_unique_channels_from_results(
                page,
                max_channels=max_results,
            )
        )

        print(
            f"Collected channels: {len(channels)}"
        )

        update_job(
            client,
            job_id=job_id,
            stage="scanning_channels",
            progress_percent=55,
        )

        results = scan_channel_list(
            browser=browser,
            channels=channels,
        )

        update_job(
            client,
            job_id=job_id,
            stage="saving_results",
            progress_percent=85,
        )

        saved_rows = save_channel_results(
            job_id=job_id,
            channels=results,
        )

        complete_job(
            client,
            job_id=job_id,
            result_count=len(
                saved_rows
            ),
        )

        print("")
        print("==============================")
        print("SCAN COMPLETED")
        print("==============================")
        print(
            f"Saved channels: {len(saved_rows)}"
        )
        print(
            "Channel data table: "
            "youtube_scan_channels"
        )
        print(
            "Job status table: "
            "youtube_scan_jobs"
        )

        return 0

    except Exception as exc:
        error_message = (
            f"{type(exc).__name__}: {exc}"
        )

        try:
            fail_job(
                client,
                job_id=job_id,
                error_message=error_message,
            )
        except Exception:
            pass

        print(
            "YouTube scan failed: "
            f"{error_message}",
            file=sys.stderr,
        )

        return 1

    finally:
        try:
            browser.stop()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run one YouTube scan job, save data, then exit."
        )
    )

    parser.add_argument(
        "keyword",
        help="YouTube search keyword.",
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=3,
        help="Maximum unique channels to scan.",
    )

    parser.add_argument(
        "--filters",
        default="{}",
        help="Optional JSON object.",
    )

    args = parser.parse_args()

    keyword = str(
        args.keyword or ""
    ).strip()

    if not keyword:
        print(
            "Keyword cannot be empty.",
            file=sys.stderr,
        )
        return 1

    try:
        filters = parse_filters(
            args.filters
        )
    except Exception as exc:
        print(
            f"Invalid filters: {exc}",
            file=sys.stderr,
        )
        return 1

    return run_scan_once(
        keyword=keyword,
        max_results=max(
            1,
            int(args.max_results),
        ),
        filters=filters,
    )


if __name__ == "__main__":
    raise SystemExit(main())
