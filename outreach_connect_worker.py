from __future__ import annotations

import sys
from dataclasses import dataclass

from supabase import Client, create_client

from app.linkedin_connect_action import (
    LinkedInConnectResult,
    connect_profile,
)
from app.outreach_result_store import (
    save_connect_result,
)
from app.outreach_scheduler import (
    OutreachScheduler,
)
from app.settings import (
    load_settings,
)


JOB_TABLE = "outreach_jobs"
TARGET_TABLE = "outreach_job_targets"
PROSPECT_TABLE = "outreach_prospects"


# =========================================================
# DATA
# =========================================================


@dataclass(frozen=True)
class OutreachTarget:
    target_id: str
    job_id: str
    prospect_id: str
    linkedin_url: str


# =========================================================
# SUPABASE
# =========================================================


def get_client() -> Client:
    settings = load_settings()

    return create_client(
        settings.outreach_supabase_url,
        settings.outreach_supabase_secret_key,
    )


# =========================================================
# LOAD JOB
# =========================================================


def load_job_by_code(
    *,
    client: Client,
    job_code: str,
) -> dict:
    response = (
        client.table(
            JOB_TABLE
        )
        .select("*")
        .eq(
            "job_code",
            job_code,
        )
        .limit(1)
        .execute()
    )

    rows = (
        response.data
        if isinstance(
            response.data,
            list,
        )
        else []
    )

    if not rows:
        raise RuntimeError(
            f"Job not found: {job_code}"
        )

    return rows[0]


# =========================================================
# LOAD TARGETS
# =========================================================


def load_pending_targets(
    *,
    client: Client,
    job_id: str,
) -> list[OutreachTarget]:
    """
    Chỉ lấy target thuộc đúng job user chọn
    và chưa được worker xử lý.
    """

    response = (
        client.table(
            TARGET_TABLE
        )
        .select(
            (
                "id,"
                "job_id,"
                "prospect_id,"
                "status,"
                "outreach_prospects("
                "linkedin_url"
                ")"
            )
        )
        .eq(
            "job_id",
            job_id,
        )
        .eq(
            "status",
            "pending",
        )
        .execute()
    )

    rows = (
        response.data
        if isinstance(
            response.data,
            list,
        )
        else []
    )

    targets: list[
        OutreachTarget
    ] = []

    for row in rows:
        prospect = (
            row.get(
                "outreach_prospects"
            )
            or {}
        )

        linkedin_url = str(
            prospect.get(
                "linkedin_url",
                "",
            )
            or ""
        ).strip()

        if not linkedin_url:
            continue

        targets.append(
            OutreachTarget(
                target_id=str(
                    row["id"]
                ),
                job_id=str(
                    row["job_id"]
                ),
                prospect_id=str(
                    row["prospect_id"]
                ),
                linkedin_url=linkedin_url,
            )
        )

    return targets


# =========================================================
# JOB STATUS
# =========================================================


def mark_job_running(
    *,
    client: Client,
    job_id: str,
) -> None:
    (
        client.table(
            JOB_TABLE
        )
        .update(
            {
                "status": "running",
            }
        )
        .eq(
            "id",
            job_id,
        )
        .execute()
    )


# =========================================================
# PROCESS ONE ACCOUNT TURN
# =========================================================


def process_account_turn(
    *,
    client: Client,
    scheduler: OutreachScheduler,
    targets: list[OutreachTarget],
) -> int:
    """
    Xử lý tối đa quota còn lại
    của account hiện tại.

    Return:
        số target đã xử lý.
    """

    if not targets:
        return 0

    turn = (
        scheduler
        .get_current_turn()
    )

    account = turn.account

    capacity = min(
        len(targets),
        turn.remaining_in_current_turn,
    )

    if capacity <= 0:
        return 0

    batch = targets[
        :capacity
    ]

    print("")
    print("=" * 60)
    print("ACCOUNT TURN")
    print("=" * 60)

    print(
        f"Account: "
        f"{account.account_id}"
    )

    print(
        "Used before: "
        f"{turn.used_in_current_turn}"
        "/"
        f"{turn.turn_limit}"
    )

    print(
        f"Batch size: {len(batch)}"
    )

    browser = (
        account
        .create_browser_manager()
    )

    processed = 0

    try:
        browser.start()

        for index, target in enumerate(
            batch,
            start=1,
        ):
            print("")
            print("-" * 60)

            print(
                f"[{index}/{len(batch)}]"
            )

            print(
                f"URL: {target.linkedin_url}"
            )

            try:
                result = connect_profile(
                    browser=browser,
                    linkedin_url=(
                        target.linkedin_url
                    ),
                )

            except Exception as exc:
                result = LinkedInConnectResult(
                    linkedin_url=(
                        target.linkedin_url
                    ),
                    final_url="",
                    status="failed",
                    message=(
                        "worker_error: "
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    ),
                )

            success = (
                save_connect_result(
                    job_id=target.job_id,
                    target_id=target.target_id,
                    prospect_id=(
                        target.prospect_id
                    ),
                    account_id=(
                        account.account_id
                    ),
                    result=result,
                    client=client,
                )
            )

            # ---------------------------------------------
            # QUOTA
            # ---------------------------------------------
            #
            # Dù success hay failed thì account
            # đã dùng 1 attempt cho profile này.
            #

            scheduler.record_profile_processed(
                amount=1
            )

            processed += 1

            print(
                "RESULT:",
                (
                    "SUCCESS"
                    if success
                    else "FAILED"
                ),
            )

            print(
                "Action status:",
                result.status,
            )

            print(
                "Message:",
                result.message,
            )

    finally:
        browser.stop()

    return processed


# =========================================================
# RUN ONE JOB
# =========================================================


def run_connect_job(
    *,
    job_code: str,
) -> None:
    settings = load_settings()

    client = get_client()

    scheduler = OutreachScheduler(
        settings=settings
    )

    # -----------------------------------------------------
    # LOAD JOB
    # -----------------------------------------------------

    job = load_job_by_code(
        client=client,
        job_code=job_code,
    )

    job_id = str(
        job["id"]
    )

    print("")
    print("=" * 60)
    print("OUTREACH CONNECT JOB")
    print("=" * 60)

    print(
        f"job_code: {job_code}"
    )

    print(
        f"job_id: {job_id}"
    )

    print(
        "input_count:",
        job.get(
            "input_count",
            0,
        ),
    )

    print(
        "target_count:",
        job.get(
            "target_count",
            0,
        ),
    )

    print(
        "duplicate_count:",
        job.get(
            "duplicate_count",
            0,
        ),
    )

    # -----------------------------------------------------
    # LOAD TARGETS
    # -----------------------------------------------------

    targets = load_pending_targets(
        client=client,
        job_id=job_id,
    )

    print(
        "pending targets:",
        len(targets),
    )

    if not targets:
        print(
            "Nothing to process."
        )
        return

    mark_job_running(
        client=client,
        job_id=job_id,
    )

    # -----------------------------------------------------
    # RUN
    # -----------------------------------------------------

    offset = 0

    while offset < len(
        targets
    ):
        remaining_targets = (
            targets[offset:]
        )

        processed = (
            process_account_turn(
                client=client,
                scheduler=scheduler,
                targets=(
                    remaining_targets
                ),
            )
        )

        if processed <= 0:
            raise RuntimeError(
                "Worker made no progress."
            )

        offset += processed

    print("")
    print("=" * 60)
    print("JOB FINISHED")
    print("=" * 60)

    print(
        f"Processed this run: "
        f"{offset}"
    )


# =========================================================
# CLI
# =========================================================


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage:"
        )

        print(
            "python3 outreach_connect_worker.py "
            "<job_code>"
        )

        raise SystemExit(1)

    job_code = str(
        sys.argv[1]
    ).strip()

    run_connect_job(
        job_code=job_code
    )


if __name__ == "__main__":
    main()
