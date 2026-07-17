from __future__ import annotations

import sys

from app.google_sheets import load_linkedin_sources
from app.settings import load_settings


def main() -> int:
    try:
        settings = load_settings()
        sources = load_linkedin_sources(settings)

        print(f"Found {len(sources)} unique LinkedIn URLs.")

        # Chỉ in thử tối đa 5 dòng để kiểm tra dữ liệu.
        for index, source in enumerate(sources[:5], start=1):
            print(
                f"{index}. {source.name} | "
                f"{source.linkedin_url} | "
                f"{source.company}"
            )

        return 0

    except Exception as exc:
        print(
            f"Google Sheet test failed: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
