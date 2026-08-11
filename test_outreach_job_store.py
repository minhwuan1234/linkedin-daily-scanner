from __future__ import annotations

from app.outreach_job_store import (
    create_connect_job,
)


TEST_URLS = [
    "https://www.linkedin.com/in/anhtuanle234/
    "https://www.linkedin.com/in/ovquang/",
    "https://www.linkedin.com/in/nguyenthaotrinh1012/",
]


def main() -> None:
    result = create_connect_job(
        TEST_URLS
    )

    print("")
    print("=" * 60)
    print("OUTREACH JOB CREATED")
    print("=" * 60)

    print(
        f"job_id: {result.job_id}"
    )

    print(
        f"job_code: {result.job_code}"
    )

    print(
        f"input_count: "
        f"{result.input_count}"
    )

    print(
        f"target_count: "
        f"{result.target_count}"
    )

    print(
        f"duplicate_count: "
        f"{result.duplicate_count}"
    )


if __name__ == "__main__":
    main()
