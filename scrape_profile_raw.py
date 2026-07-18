from __future__ import annotations

import json
import sys
from pathlib import Path

from app.profile_raw_scraper import (
    OUTPUT_DIR,
    scrape_profile_raw,
)
from app.settings import load_settings


def main() -> int:
    try:
        settings = load_settings()
        result = scrape_profile_raw(settings)

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

        profile = result.get("profile", {})

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
