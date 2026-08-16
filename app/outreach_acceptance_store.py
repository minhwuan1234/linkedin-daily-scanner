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
# RESOLVE CONNECT JOB
# =========================================================

def resolve_source_job_id(
    source_job_id_or_code: str,
    *,
    client: Client | None = None,
) -> str:
    """
    Accept either:
    - outreach_jobs.id UUID
    - outreach_jobs.job_code, e.g. 1-20260816-01

    Always return the canonical outreach_jobs.id UUID.
    """

    cleaned = str(
        source_job_id_or_code
        or ""
    ).strip()

    if not cleaned:
        raise OutreachAcceptanceStoreError(
            "source_job_id is required."
        )

    active_client = (
        client
        if client is not None
        else get_outreach_supabase_client()
    )

    # First try UUID/id only when it looks like a UUID.
    # This avoids Postgres uuid parse errors for job_code values.
    looks_like_uuid = (
        len(cleaned) == 36
        and cleaned.count("-") == 4
    )

    if looks_like_uuid:
        response = (
            active_client.table(
                JOB_TABLE
            )
            .select(
                "id,job_code"
            )
            .eq(
                "id",
                cleaned,
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

        if rows:
            return str(
                rows[0]["id"]
            )

    # Fallback / explicit job_code lookup.
    response = (
        active_client.table(
            JOB_TABLE
        )
        .select(
            "id,job_code"
        )
        .eq(
            "job_code",
            cleaned,
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
            "Connect Job not found by id or job_code: "
            f"{cleaned}"
        )

    return str(
        rows[0]["id"]
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

    resolved_job_id = resolve_source_job_id(
        source_job_id,
        client=active_client,
    )

    targets = load_acceptance_targets(
        source_job_id=resolved_job_id,
        client=active_client,
    )

    return create_acceptance_check_run(
        source_job_id=resolved_job_id,
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
    Load finished targets from the selected Connect Job that
    still need Acceptance Check.

    FIX:
    The previous implementation filtered too aggressively:
    - target.status had to be exactly "completed";
    - outreach_prospects.connect_status had to be exactly
      "invitation_sent".

    That can hide real profiles from Acceptance Check, including
    profiles that the Connect flow misclassified as unavailable even
    though LinkedIn already shows "Remove connection".

    New rule:
    - same source job;
    - acceptance_status != accepted;
    - assigned_account_id exists;
    - LinkedIn URL exists;
    - target is finished: completed OR failed.

    Acceptance Checker itself is read-only and is the authority for
    the current LinkedIn relationship state.
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

    cleaned_job_id = resolve_source_job_id(
        cleaned_job_id,
        client=active_client,
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
        target_status = str(
            row.get(
                "status",
                "",
            )
            or ""
        ).strip()

        # Only inspect finished Connect targets.
        # Do not touch pending/running work.
        if target_status not in {
            "completed",
            "failed",
        }:
            continue

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
                "connect_status": str(
                    prospect.get(
                        "connect_status",
                        "",
                    )
                    or ""
                ).strip(),
                "target_status": target_status,
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
