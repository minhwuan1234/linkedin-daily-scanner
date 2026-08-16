from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from supabase import Client

from app.linkedin_acceptance_checker import (
    LinkedInAcceptanceResult,
)
from app.outreach_result_store import (
    get_outreach_supabase_client,
)


ACCEPTANCE_CHECK_TABLE = (
    "outreach_acceptance_checks"
)

TARGET_TABLE = (
    "outreach_job_targets"
)

PROSPECT_TABLE = (
    "outreach_prospects"
)


class OutreachAcceptanceStoreError(
    RuntimeError
):
    pass


def _utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


# =========================================================
# CREATE CHECK RUN
# =========================================================

def _get_next_run_number(
    *,
    client: Client,
    source_job_id: str,
) -> int:
    response = (
        client.table(
            ACCEPTANCE_CHECK_TABLE
        )
        .select(
            "run_number"
        )
        .eq(
            "source_job_id",
            source_job_id,
        )
        .order(
            "run_number",
            desc=True,
        )
        .limit(
            1
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

    if not rows:
        return 1

    current = int(
        rows[0].get(
            "run_number",
            0,
        )
        or 0
    )

    return current + 1


def create_acceptance_check_run(
    *,
    source_job_id: str,
    total_to_check: int,
    status: str = "running",
    client: Client | None = None,
) -> dict:
    cleaned_job_id = str(
        source_job_id
        or ""
    ).strip()

    if not cleaned_job_id:
        raise OutreachAcceptanceStoreError(
            "source_job_id is required."
        )

    active_client = (
        client
        if client is not None
        else get_outreach_supabase_client()
    )

    run_number = (
        _get_next_run_number(
            client=active_client,
            source_job_id=(
                cleaned_job_id
            ),
        )
    )

    cleaned_status = str(
        status
        or ""
    ).strip()

    if cleaned_status not in {
        "pending",
        "running",
    }:
        raise OutreachAcceptanceStoreError(
            "status must be 'pending' or 'running'."
        )

    now = _utc_now()

    response = (
        active_client.table(
            ACCEPTANCE_CHECK_TABLE
        )
        .insert(
            {
                "source_job_id": (
                    cleaned_job_id
                ),
                "run_number": run_number,
                "status": cleaned_status,
                "total_to_check": max(
                    0,
                    int(total_to_check),
                ),
                "checked_count": 0,
                "new_accepted_count": 0,
                "still_pending_count": 0,
                "declined_or_unknown_count": 0,
                "failed_count": 0,
                "started_at": (
                    now
                    if cleaned_status == "running"
                    else None
                ),
                "updated_at": now,
            }
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

    if not rows:
        raise OutreachAcceptanceStoreError(
            "Could not create acceptance check run."
        )

    return rows[0]



# =========================================================
# QUEUE CHECK RUN FROM RAILWAY
# =========================================================

def queue_acceptance_check_run(
    *,
    source_job_id: str,
    client: Client | None = None,
) -> dict:
    """
    Railway-facing helper.

    It does NOT run LinkedIn.
    It only:
    1. loads eligible targets for the selected Connect Job;
    2. creates one acceptance run with status='pending'.

    The Mac acceptance worker will claim this row later.
    """
    active_client = (
        client
        if client is not None
        else get_outreach_supabase_client()
    )

    targets = load_acceptance_targets(
        source_job_id=source_job_id,
        client=active_client,
    )

    return create_acceptance_check_run(
        source_job_id=source_job_id,
        total_to_check=len(targets),
        status="pending",
        client=active_client,
    )


# =========================================================
# LOAD TARGETS TO CHECK
# =========================================================

def load_acceptance_targets(
    *,
    source_job_id: str,
    client: Client | None = None,
) -> list[dict]:
    """
    Load only targets that belong to the selected Connect Job
    and still need acceptance checking.

    We require:
    - target.status == completed
    - assigned_account_id is present
    - acceptance_status != accepted

    This includes:
    - not_checked
    - pending
    - declined_or_unknown
    - check_failed

    Accepted targets are never reopened.
    """
    cleaned_job_id = str(
        source_job_id
        or ""
    ).strip()

    if not cleaned_job_id:
        raise OutreachAcceptanceStoreError(
            "source_job_id is required."
        )

    active_client = (
        client
        if client is not None
        else get_outreach_supabase_client()
    )

    response = (
        active_client.table(
            TARGET_TABLE
        )
        .select(
            (
                "id,"
                "job_id,"
                "prospect_id,"
                "status,"
                "assigned_account_id,"
                "acceptance_status,"
                "acceptance_check_count,"
                "outreach_prospects("
                "linkedin_url,"
                "connect_status"
                ")"
            )
        )
        .eq(
            "job_id",
            cleaned_job_id,
        )
        .eq(
            "status",
            "completed",
        )
        .neq(
            "acceptance_status",
            "accepted",
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

    targets: list[dict] = []

    for row in rows:
        account_id = str(
            row.get(
                "assigned_account_id",
                "",
            )
            or ""
        ).strip()

        if not account_id:
            continue

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

        # Production safety:
        # only follow profiles the tool believes were sent/pending.
        connect_status = str(
            prospect.get(
                "connect_status",
                "",
            )
            or ""
        ).strip()

        if connect_status != "invitation_sent":
            continue

        targets.append(
            {
                "target_id": str(
                    row["id"]
                ),
                "job_id": str(
                    row["job_id"]
                ),
                "prospect_id": str(
                    row["prospect_id"]
                ),
                "account_id": account_id,
                "linkedin_url": linkedin_url,
                "acceptance_status": str(
                    row.get(
                        "acceptance_status",
                        "not_checked",
                    )
                    or "not_checked"
                ),
                "acceptance_check_count": int(
                    row.get(
                        "acceptance_check_count",
                        0,
                    )
                    or 0
                ),
            }
        )

    return targets


# =========================================================
# SAVE ONE TARGET RESULT
# =========================================================

def save_acceptance_result(
    *,
    target_id: str,
    result: LinkedInAcceptanceResult,
    client: Client | None = None,
) -> None:
    cleaned_target_id = str(
        target_id
        or ""
    ).strip()

    if not cleaned_target_id:
        raise OutreachAcceptanceStoreError(
            "target_id is required."
        )

    active_client = (
        client
        if client is not None
        else get_outreach_supabase_client()
    )

    now = _utc_now()

    # Read current count first.
    response = (
        active_client.table(
            TARGET_TABLE
        )
        .select(
            (
                "acceptance_check_count,"
                "accepted_at"
            )
        )
        .eq(
            "id",
            cleaned_target_id,
        )
        .limit(
            1
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

    if not rows:
        raise OutreachAcceptanceStoreError(
            f"Target not found: {cleaned_target_id}"
        )

    current_count = int(
        rows[0].get(
            "acceptance_check_count",
            0,
        )
        or 0
    )

    existing_accepted_at = (
        rows[0].get(
            "accepted_at"
        )
    )

    update_data = {
        "acceptance_status": (
            result.status
        ),
        "acceptance_checked_at": now,
        "acceptance_check_count": (
            current_count + 1
        ),
        "updated_at": now,
    }

    if (
        result.status == "accepted"
        and not existing_accepted_at
    ):
        update_data[
            "accepted_at"
        ] = now

    (
        active_client.table(
            TARGET_TABLE
        )
        .update(
            update_data
        )
        .eq(
            "id",
            cleaned_target_id,
        )
        .execute()
    )


# =========================================================
# CHECK RUN COUNTERS
# =========================================================

def update_acceptance_check_run(
    *,
    check_id: str,
    checked_count: int,
    new_accepted_count: int,
    still_pending_count: int,
    declined_or_unknown_count: int,
    failed_count: int,
    completed: bool = False,
    failed: bool = False,
    client: Client | None = None,
) -> None:
    cleaned_check_id = str(
        check_id
        or ""
    ).strip()

    if not cleaned_check_id:
        raise OutreachAcceptanceStoreError(
            "check_id is required."
        )

    active_client = (
        client
        if client is not None
        else get_outreach_supabase_client()
    )

    now = _utc_now()

    update_data = {
        "checked_count": max(
            0,
            int(checked_count),
        ),
        "new_accepted_count": max(
            0,
            int(new_accepted_count),
        ),
        "still_pending_count": max(
            0,
            int(still_pending_count),
        ),
        "declined_or_unknown_count": max(
            0,
            int(
                declined_or_unknown_count
            ),
        ),
        "failed_count": max(
            0,
            int(failed_count),
        ),
        "updated_at": now,
    }

    if failed:
        update_data[
            "status"
        ] = "failed"
        update_data[
            "completed_at"
        ] = now

    elif completed:
        update_data[
            "status"
        ] = "completed"
        update_data[
            "completed_at"
        ] = now

    (
        active_client.table(
            ACCEPTANCE_CHECK_TABLE
        )
        .update(
            update_data
        )
        .eq(
            "id",
            cleaned_check_id,
        )
        .execute()
    )


# =========================================================
# GROUP BY ACCOUNT
# =========================================================

def group_targets_by_account(
    targets: Iterable[dict],
) -> dict[str, list[dict]]:
    grouped: dict[
        str,
        list[dict],
    ] = {}

    for target in targets:
        account_id = str(
            target.get(
                "account_id",
                "",
            )
            or ""
        ).strip()

        if not account_id:
            continue

        grouped.setdefault(
            account_id,
            [],
        ).append(
            target
        )

    return grouped
