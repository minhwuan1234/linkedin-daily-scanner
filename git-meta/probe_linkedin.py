from __future__ import annotations

import sys

from app.linkedin_scanner import probe_linkedin_source
from app.settings import load_settings


def main() -> int:
    try:
        settings = load_settings()

        result = probe_linkedin_source(settings)

        print("LinkedIn probe completed.")
        print(f"Source ID: {result.source_id}")
        print(f"Requested URL: {result.linkedin_url}")
        print(f"Final URL: {result.final_url}")
        print(f"Page title: {result.page_title}")
        print(f"Body preview: {result.body_preview}")

        return 0

    except Exception as exc:
        print(
            f"LinkedIn probe failed: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
