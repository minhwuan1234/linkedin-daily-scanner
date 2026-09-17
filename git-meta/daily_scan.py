from __future__ import annotations

import sys
from datetime import datetime

from app.google_sheets import (
    load_linkedin_sources,
)
from app.settings import load_settings
from app.source_sync import (
    sync_sources_to_supabase,
)
from scan_unscanned_profiles import (
    main as scan_unscanned_main,
)


def print_separator() -> None:
    print("")
    print("=" * 70)
    print("")


def main() -> int:
    started_at = datetime.now()

    print("")
    print("LinkedIn daily pipeline started.")
    print(
        "Started at: "
        f"{started_at.isoformat(timespec='seconds')}"
    )

    try:
        settings = load_settings()

        # -------------------------------------------------
        # Bước 1: đọc danh sách URL từ Google Sheet
        # -------------------------------------------------

        print_separator()
        print("Starting: Google Sheet source loading")
        print_separator()

        sources = load_linkedin_sources(
            settings
        )

        print("")
        print(
            "Completed: Google Sheet source loading"
        )
        print(
            f"Sources loaded: {len(sources)}"
        )

        # -------------------------------------------------
        # Bước 2: sync URL từ Sheet sang Supabase
        # -------------------------------------------------

        print_separator()
        print("Starting: Google Sheet source sync")
        print_separator()

        sync_result = sync_sources_to_supabase(
            settings,
            sources,
        )

        print("")
        print(
            "Completed: Google Sheet source sync"
        )
        print(
            f"Sync result: {sync_result}"
        )

        # -------------------------------------------------
        # Bước 3: scan các source chưa từng scan
        # -------------------------------------------------

        print_separator()
        print(
            "Starting: Unscanned LinkedIn profiles"
        )
        print_separator()

        scan_exit_code = scan_unscanned_main()

        if scan_exit_code != 0:
            raise RuntimeError(
                "Unscanned profile scan completed "
                f"with exit code {scan_exit_code}."
            )

        finished_at = datetime.now()
        duration = finished_at - started_at

        print_separator()
        print("LinkedIn daily pipeline completed.")
        print(
            "Finished at: "
            f"{finished_at.isoformat(timespec='seconds')}"
        )
        print(
            f"Duration: {duration}"
        )

        return 0

    except Exception as exc:
        finished_at = datetime.now()
        duration = finished_at - started_at

        print_separator()
        print(
            "LinkedIn daily pipeline failed: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        print(
            "Finished at: "
            f"{finished_at.isoformat(timespec='seconds')}",
            file=sys.stderr,
        )
        print(
            f"Duration: {duration}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
