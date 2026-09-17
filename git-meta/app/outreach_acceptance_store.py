from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Iterable

from supabase import Client, create_client

from app.settings import load_settings

if TYPE_CHECKING:
    from app.linkedin_acceptance_checker import (
        LinkedInAcceptanceResult,
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

JOB_TABLE = (
    "outreach_jobs"
)

MESSAGE_TARGET_TABLE = (
    "outreach_message_targets"
)

MESSAGE_BATCH_TABLE = (
    "outreach_message_batches"
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
# SUPABASE
# =========================================================

def get_outreach_supabase_client() -> Client:
    """
    Backend-safe Outreach Supabase client.

    Important:
    this module must NOT import LinkedIn browser/action modules
    at runtime because Railway only queues/reads DB work.
    """
    settings = load_settings()

    if not settings.outreach_supabase_url:
        raise OutreachAcceptanceStoreError(
            "Missing OUTREACH_SUPABASE_URL."
        )

    if not settings.outreach_supabase_secret_key:
        raise OutreachAcceptanceStoreError(
            "Missing OUTREACH_SUPABASE_SECRET_KEY."
        )

    return create_client(
        settings.outreach_supabase_url,
        settings.outreach_supabase_secret_key,
    )


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
# CLAIM NEXT PENDING CHECK RUN
# =========================================================

def claim_next_pending_acceptance_check(
    *,
    client: Client | None = None,
) -> dict | None:
    """
    Mac worker helper.

    Find the oldest pending Acceptance Check and move it to running.

    Current system uses one Acceptance Worker, so a simple
    select -> conditional update is sufficient for now.

    The conditional update includes status='pending' so a row that
    has already been claimed will not be claimed again.
    """
    active_client = (
        client
        if client is not None
        else get_outreach_supabase_client()
    )

    response = (
        active_client.table(
            ACCEPTANCE_CHECK_TABLE
        )
        .select(
            (
                "id,"
                "source_job_id,"
                "run_number,"
                "status,"
                "total_to_check,"
                "created_at"
            )
        )
        .eq(
            "status",
            "pending",
        )
        .order(
            "created_at",
            desc=False,
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
        return None

    candidate = rows[0]

    check_id = str(
        candidate.get(
            "id",
            "",
        )
        or ""
    ).strip()

    if not check_id:
        return None

    now = _utc_now()

    claim_response = (
        active_client.table(
            ACCEPTANCE_CHECK_TABLE
        )
        .update(
            {
                "status": "running",
                "started_at": now,
                "updated_at": now,
            }
        )
        .eq(
            "id",
            check_id,
        )
        .eq(
            "status",
            "pending",
        )
        .execute()
    )

    claimed_rows = (
        claim_response.data
        if isinstance(
            claim_response.data,
            list,
        )
        else []
    )

    if not claimed_rows:
        return None

    return claimed_rows[0]


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
    result: "LinkedInAcceptanceResult",
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

# =========================================================
# ACCEPTANCE CHECK HISTORY
# =========================================================

def list_acceptance_check_history(
    *,
    source_job_id: str,
    client: Client | None = None,
) -> list[dict]:
    """
    Read every Acceptance Check run for one Connect Job.

    Read-only.
    Newest run is returned first.
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
        active_client
        .table(
            ACCEPTANCE_CHECK_TABLE
        )
        .select(
            (
                "id,"
                "source_job_id,"
                "run_number,"
                "status,"
                "total_to_check,"
                "checked_count,"
                "new_accepted_count,"
                "still_pending_count,"
                "declined_or_unknown_count,"
                "failed_count,"
                "created_at,"
                "started_at,"
                "completed_at,"
                "updated_at"
            )
        )
        .eq(
            "source_job_id",
            cleaned_job_id,
        )
        .order(
            "run_number",
            desc=True,
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

    return [
        {
            "id": str(
                row.get(
                    "id",
                    "",
                )
                or ""
            ).strip(),
            "source_job_id": str(
                row.get(
                    "source_job_id",
                    "",
                )
                or ""
            ).strip(),
            "run_number": int(
                row.get(
                    "run_number",
                    0,
                )
                or 0
            ),
            "status": str(
                row.get(
                    "status",
                    "",
                )
                or ""
            ).strip(),
            "total_to_check": int(
                row.get(
                    "total_to_check",
                    0,
                )
                or 0
            ),
            "checked_count": int(
                row.get(
                    "checked_count",
                    0,
                )
                or 0
            ),
            "new_accepted_count": int(
                row.get(
                    "new_accepted_count",
                    0,
                )
                or 0
            ),
            "still_pending_count": int(
                row.get(
                    "still_pending_count",
                    0,
                )
                or 0
            ),
            "declined_or_unknown_count": int(
                row.get(
                    "declined_or_unknown_count",
                    0,
                )
                or 0
            ),
            "failed_count": int(
                row.get(
                    "failed_count",
                    0,
                )
                or 0
            ),
            "created_at": row.get(
                "created_at"
            ),
            "started_at": row.get(
                "started_at"
            ),
            "completed_at": row.get(
                "completed_at"
            ),
            "updated_at": row.get(
                "updated_at"
            ),
        }
        for row in rows
    ]

# =========================================================
# DELETE CONNECT JOB
# =========================================================

def delete_connect_job_data(
    *,
    source_job_id: str,
    client: Client | None = None,
) -> dict:
    """
    Permanently delete one completed Connect Job and its dependent data.

    Deletes:
    - Acceptance Check history
    - message target snapshots sourced from this Connect Job
    - Connect Job targets
    - Connect Job row
    - empty message batches left after snapshot deletion
    - orphan prospects no longer referenced anywhere

    Shared prospects referenced by other jobs are preserved.

    Safety:
    - active Connect Jobs cannot be deleted
    - jobs with an active Acceptance Check cannot be deleted
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

    # 1) Read job + protect active work.
    job_response = (
        active_client
        .table(JOB_TABLE)
        .select("id,job_code,status")
        .eq("id", cleaned_job_id)
        .limit(1)
        .execute()
    )

    job_rows = (
        job_response.data
        if isinstance(job_response.data, list)
        else []
    )

    if not job_rows:
        raise OutreachAcceptanceStoreError(
            f"Connect Job not found: {cleaned_job_id}"
        )

    job = job_rows[0]
    job_status = str(
        job.get("status", "")
        or ""
    ).strip().lower()

    if job_status in {
        "pending",
        "running",
        "processing",
        "starting",
    }:
        raise OutreachAcceptanceStoreError(
            "Active Connect Job cannot be deleted."
        )

    active_check_response = (
        active_client
        .table(ACCEPTANCE_CHECK_TABLE)
        .select("id,status")
        .eq("source_job_id", cleaned_job_id)
        .in_("status", ["pending", "running"])
        .limit(1)
        .execute()
    )

    active_checks = (
        active_check_response.data
        if isinstance(active_check_response.data, list)
        else []
    )

    if active_checks:
        raise OutreachAcceptanceStoreError(
            "Connect Job has an active Acceptance Check."
        )

    # 2) Collect source target IDs + prospects.
    target_response = (
        active_client
        .table(TARGET_TABLE)
        .select("id,prospect_id")
        .eq("job_id", cleaned_job_id)
        .execute()
    )

    target_rows = (
        target_response.data
        if isinstance(target_response.data, list)
        else []
    )

    target_ids = [
        str(row.get("id", "") or "").strip()
        for row in target_rows
        if str(row.get("id", "") or "").strip()
    ]

    prospect_ids = {
        str(row.get("prospect_id", "") or "").strip()
        for row in target_rows
        if str(row.get("prospect_id", "") or "").strip()
    }

    # 3) Delete downstream message snapshots first because
    # source_target_id uses ON DELETE RESTRICT.
    affected_batch_ids: set[str] = set()
    deleted_message_targets = 0

    if target_ids:
        message_response = (
            active_client
            .table(MESSAGE_TARGET_TABLE)
            .select("id,batch_id")
            .in_("source_target_id", target_ids)
            .execute()
        )

        message_rows = (
            message_response.data
            if isinstance(message_response.data, list)
            else []
        )

        deleted_message_targets = len(message_rows)

        affected_batch_ids = {
            str(row.get("batch_id", "") or "").strip()
            for row in message_rows
            if str(row.get("batch_id", "") or "").strip()
        }

        (
            active_client
            .table(MESSAGE_TARGET_TABLE)
            .delete()
            .in_("source_target_id", target_ids)
            .execute()
        )

    # 4) Keep affected message batches internally consistent.
    deleted_message_batches = 0

    for batch_id in affected_batch_ids:
        remaining_response = (
            active_client
            .table(MESSAGE_TARGET_TABLE)
            .select("status")
            .eq("batch_id", batch_id)
            .execute()
        )

        remaining = (
            remaining_response.data
            if isinstance(remaining_response.data, list)
            else []
        )

        if not remaining:
            (
                active_client
                .table(MESSAGE_BATCH_TABLE)
                .delete()
                .eq("id", batch_id)
                .execute()
            )
            deleted_message_batches += 1
            continue

        target_count = len(remaining)
        sent_count = sum(
            1
            for row in remaining
            if str(row.get("status", "") or "").strip().lower()
            == "sent"
        )
        failed_count = sum(
            1
            for row in remaining
            if str(row.get("status", "") or "").strip().lower()
            == "failed"
        )
        processed_count = sent_count + failed_count

        (
            active_client
            .table(MESSAGE_BATCH_TABLE)
            .update(
                {
                    "target_count": target_count,
                    "processed_count": processed_count,
                    "sent_count": sent_count,
                    "failed_count": failed_count,
                    "updated_at": _utc_now(),
                }
            )
            .eq("id", batch_id)
            .execute()
        )

    # 5) Delete acceptance history + job targets + job.
    (
        active_client
        .table(ACCEPTANCE_CHECK_TABLE)
        .delete()
        .eq("source_job_id", cleaned_job_id)
        .execute()
    )

    (
        active_client
        .table(TARGET_TABLE)
        .delete()
        .eq("job_id", cleaned_job_id)
        .execute()
    )

    (
        active_client
        .table(JOB_TABLE)
        .delete()
        .eq("id", cleaned_job_id)
        .execute()
    )

    # 6) Remove only prospects that became true orphans.
    deleted_orphan_prospects = 0

    for prospect_id in prospect_ids:
        other_target_response = (
            active_client
            .table(TARGET_TABLE)
            .select("id")
            .eq("prospect_id", prospect_id)
            .limit(1)
            .execute()
        )

        if (
            isinstance(other_target_response.data, list)
            and other_target_response.data
        ):
            continue

        other_message_response = (
            active_client
            .table(MESSAGE_TARGET_TABLE)
            .select("id")
            .eq("prospect_id", prospect_id)
            .limit(1)
            .execute()
        )

        if (
            isinstance(other_message_response.data, list)
            and other_message_response.data
        ):
            continue

        (
            active_client
            .table(PROSPECT_TABLE)
            .delete()
            .eq("id", prospect_id)
            .execute()
        )

        deleted_orphan_prospects += 1

    return {
        "job_id": cleaned_job_id,
        "job_code": str(
            job.get("job_code", "")
            or ""
        ).strip(),
        "deleted_targets": len(target_ids),
        "deleted_message_targets": deleted_message_targets,
        "deleted_message_batches": deleted_message_batches,
        "deleted_orphan_prospects": deleted_orphan_prospects,
    }

