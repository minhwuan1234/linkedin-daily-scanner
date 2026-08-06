from __future__ import annotations

import json
import uuid

from app.youtube_result_store import (
    build_channel_row,
    save_channel_result,
)


def main() -> None:
    test_channel = {
        "channel_url": (
            "https://www.youtube.com/"
            "@youtube_result_store_test"
        ),
        "channel_name": (
            "YouTube Result Store Test"
        ),
        "subscriber_count_text": (
            "1.15M subscribers"
        ),
        "subscriber_count": 1_150_000,
        "video_count_text": "208 videos",
        "video_count": 208,
        "channel_description": (
            "Temporary test row created by "
            "test_youtube_result_store.py"
        ),
        "location": "United Kingdom",
        "email": "",
        "email_status": "login_required",
        "total_views_text": (
            "82,362,462 views"
        ),
        "total_views": 82_362_462,
        "channel_links": [
            {
                "title": "Website",
                "url": "https://example.com",
            },
            {
                "title": "Course",
                "url": "https://example.com/course",
            },
        ],
        "scan_status": "test",
    }

    job_id = str(
    uuid.uuid4()
    )
  
    print("")
    print("==============================")
    print("ROW PREVIEW")
    print("==============================")

    row = build_channel_row(
        job_id=job_id,
        channel=test_channel,
    )

    print(
        json.dumps(
            row,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )

    print("")
    print("==============================")
    print("SUPABASE INSERT")
    print("==============================")

    saved = save_channel_result(
        job_id=job_id,
        channel=test_channel,
    )

    print(
        json.dumps(
            saved,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )

    print("")
    print("INSERT SUCCESS")


if __name__ == "__main__":
    main()
