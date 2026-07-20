from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

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


def get_unscanned_sources(
    settings: Settings,
) -> list[dict[str, Any]]:
    client = create_supabase_client(settings)

    response = (
        client.table("linkedin_sources")
        .select(
            "id,name,linkedin_url,"
            "source_type,last_scanned_at"
        )
        .eq("enabled", True)
        .is_("last_scanned_at", "null")
        .order("id", desc=False)
        .execute()
    )

    return list(response.data or [])


def save_local_output(
    result: dict[str, Any],
) -> Path:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_id = int(result["source_id"])

    output_path = Path(
        OUTPUT_DIR,
        f"profile_{source_id}.json",
    )

    output_path.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return output_path


def main() -> int:
    settings = load_settings()

    sources = get_unscanned_sources(
        settings
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

    success_count = 0
    failed_count = 0

    for index, source in enumerate(
        sources,
        start=1,
    ):
        source_id = int(source["id"])
        linkedin_url = str(
            source.get("linkedin_url", "")
        )

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

        try:
            result = scrape_profile_raw(
                settings=settings,
                source_id=source_id,
            )

            output_path = save_local_output(
                result
            )

            snapshot_id = save_profile_snapshot(
                settings=settings,
                result=result,
            )

            mark_source_scanned(
                settings=settings,
                source_id=source_id,
                scanned_at=result["scraped_at"],
            )

            success_count += 1

            print(
                f"Completed source {source_id}."
            )
            print(
                f"Snapshot ID: {snapshot_id}"
            )
            print(
                f"Output: {output_path.resolve()}"
            )

        except Exception as exc:
            failed_count += 1

            print(
                f"Failed source {source_id}: "
                f"{type(exc).__name__}: {exc}",
                file=sys.stderr,
            )

            # Không dừng toàn bộ batch.
            # Chuyển sang profile tiếp theo.
            continue

    print("")
    print(
        "=" * 60
    )
    print("Batch scan completed.")
    print(
        f"Total: {total}"
    )
    print(
        f"Success: {success_count}"
    )
    print(
        f"Failed: {failed_count}"
    )

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
