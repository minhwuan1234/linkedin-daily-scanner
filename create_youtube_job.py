from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from app.linkedin_scanner import (
    create_supabase_client,
)
from app.settings import load_settings


JOB_TABLE = "youtube_scan_jobs"


def create_youtube_job(
    *,
    keyword: str,
    max_results: int,
    filters: dict[str, Any],
) -> dict[str, Any]:
    cleaned_keyword = str(
        keyword or "",
    ).strip()

    if not cleaned_keyword:
        raise ValueError(
            "keyword cannot be empty"
        )

    settings = load_settings()

    client = create_supabase_client(
        settings,
    )

    payload = {
        "keyword": cleaned_keyword,
        "status": "pending",
        "current_stage": "queued",
        "progress_percent": 0,
        "max_results": max(
            1,
            int(max_results),
        ),
        "filters": filters,
        "retry_count": 0,
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

    return dict(
        rows[0]
    )


def parse_filters(
    raw_value: str,
) -> dict[str, Any]:
    cleaned = str(
        raw_value or "",
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create a real pending YouTube scan job."
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
        help=(
            "Optional JSON object stored in the job."
        ),
    )

    args = parser.parse_args()

    try:
        filters = parse_filters(
            args.filters
        )

        job = create_youtube_job(
            keyword=args.keyword,
            max_results=args.max_results,
            filters=filters,
        )

    except Exception as exc:
        print(
            "Could not create YouTube job: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1

    print("")
    print("==============================")
    print("YOUTUBE JOB CREATED")
    print("==============================")
    print(f"Job ID: {job.get('id', '')}")
    print(f"Keyword: {job.get('keyword', '')}")
    print(f"Status: {job.get('status', '')}")
    print(
        "Max results:",
        job.get(
            "max_results",
            "",
        ),
    )
    print("")
    print(
        "The running youtube_worker.py "
        "will claim this job automatically."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
