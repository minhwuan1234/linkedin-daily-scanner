from __future__ import annotations

import sys

from app.google_sheets import load_linkedin_sources
from app.settings import load_settings
from app.source_sync import sync_sources_to_supabase


def main() -> int:
    try:
        settings = load_settings()

        print("Reading LinkedIn sources from Google Sheet...")

        sources = load_linkedin_sources(settings)

        print(
            f"Found {len(sources)} unique valid LinkedIn URLs."
        )

        synced_count = sync_sources_to_supabase(
            settings=settings,
            sources=sources,
        )

        print(
            f"Successfully synced {synced_count} sources "
            "to Supabase."
        )

        return 0

    except Exception as exc:
        print(
            f"Daily source sync failed: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
