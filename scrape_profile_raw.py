from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.profile_raw_scraper import (
    OUTPUT_DIR,
    scrape_profile_raw,
)
from app.profile_snapshot_store import (
    mark_source_scanned,
    save_profile_snapshot,
)
from app.settings import load_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scrape raw LinkedIn profile data."
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

    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        settings = load_settings()

        result = scrape_profile_raw(
            settings=settings,
            source_id=args.source_id,
        )

        OUTPUT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        source_id = result["source_id"]

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

        snapshot_id = save_profile_snapshot(
            settings=settings,
            result=result,
        )

        mark_source_scanned(
            settings=settings,
            source_id=source_id,
            scanned_at=result["scraped_at"],
        )

        profile = result.get(
            "profile",
            {},
        )

        experience_raw_text = result.get(
            "experience_raw_text",
            "",
        )

        errors = result.get(
            "errors",
            [],
        )

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
            f"{len(profile.get('about_text', ''))}"
        )
        print(
            "Experience raw length: "
            f"{len(experience_raw_text)}"
        )
        print(
            f"Section errors: {len(errors)}"
        )

        print("")
        print(
            f"Output: {output_path.resolve()}"
        )

        return 0

    except Exception as exc:
        print(
            "LinkedIn raw profile scrape failed: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
