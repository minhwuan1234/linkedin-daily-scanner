from __future__ import annotations

from supabase import Client, create_client

from app.settings import (
    Settings,
    load_settings,
)


JOB_TABLE = "outreach_jobs"
SCHEDULER_TABLE = "outreach_scheduler_state"
ACCOUNT_TABLE = "outreach_accounts"

SCHEDULER_NAME = "linkedin_outreach"


class OutreachDashboardStoreError(
    RuntimeError
):
    pass


# =========================================================
# CLIENT
# =========================================================


def get_outreach_client(
    settings: Settings | None = None,
) -> Client:
    active_settings = (
        settings
        if settings is not None
        else load_settings()
    )

    if not (
        active_settings
        .outreach_supabase_url
    ):
        raise OutreachDashboardStoreError(
            "Missing OUTREACH_SUPABASE_URL."
        )

    if not (
        active_settings
        .outreach_supabase_secret_key
    ):
        raise OutreachDashboardStoreError(
            "Missing OUTREACH_SUPABASE_SECRET_KEY."
        )

    return create_client(
        active_settings.outreach_supabase_url,
        active_settings.outreach_supabase_secret_key,
    )


# =========================================================
# HELPERS
# =========================================================


def _to_int(
    value,
) -> int:
    try:
        return int(
            value or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        return 0


def _normalize_job(
    row: dict,
) -> dict:
    target_count = _to_int(
        row.get(
            "target_count"
        )
    )

    processed_count = _to_int(
        row.get(
            "processed_count"
        )
    )

    progress_percent = 0

    if target_count > 0:
        progress_percent = min(
            100,
            round(
                processed_count
                / target_count
                * 100
            ),
        )

    elif str(
        row.get(
            "status",
            "",
        )
    ) == "completed":
        progress_percent = 100

    return {
        "id": str(
            row.get(
                "id",
                "",
            )
            or ""
        ),

        "job_code": str(
            row.get(
                "job_code",
                "",
            )
            or ""
        ),

        "job_type": str(
            row.get(
                "job_type",
                "",
            )
            or ""
        ),

        "status": str(
            row.get(
                "status",
                "",
            )
            or ""
        ),

        "input_count": _to_int(
            row.get(
                "input_count"
            )
        ),

        "target_count": (
            target_count
        ),

        "duplicate_count": _to_int(
            row.get(
                "duplicate_count"
            )
        ),

        "invalid_count": _to_int(
            row.get(
                "invalid_count"
            )
        ),

        "processed_count": (
            processed_count
        ),

        "success_count": _to_int(
            row.get(
                "success_count"
            )
        ),

        "failed_count": _to_int(
            row.get(
                "failed_count"
            )
        ),

        "progress_percent": (
            progress_percent
        ),

        "last_error": (
            row.get(
                "last_error"
            )
        ),

        "created_at": (
            row.get(
                "created_at"
            )
        ),

        "started_at": (
            row.get(
                "started_at"
            )
        ),

        "completed_at": (
            row.get(
                "completed_at"
            )
        ),

        "updated_at": (
            row.get(
                "updated_at"
            )
        ),
    }


# =========================================================
# CURRENT JOB
# =========================================================


def get_current_job(
    *,
    client: Client,
) -> dict | None:
    """
    Ưu tiên job đang chạy.

    Nếu không có running:
    lấy job pending cũ nhất.

    Nếu không có pending:
    lấy job mới nhất.
    """

    select_fields = (
        "id,"
        "job_code,"
        "job_type,"
        "status,"
        "input_count,"
        "target_count,"
        "duplicate_count,"
        "invalid_count,"
        "processed_count,"
        "success_count,"
        "failed_count,"
        "last_error,"
        "created_at,"
        "started_at,"
        "completed_at,"
        "updated_at"
    )

    # -----------------------------------------------------
    # RUNNING
    # -----------------------------------------------------

    response = (
        client
        .table(
            JOB_TABLE
        )
        .select(
            select_fields
        )
        .eq(
            "job_type",
            "connect",
        )
        .eq(
            "status",
            "running",
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

    rows = list(
        response.data
        or []
    )

    if rows:
        return _normalize_job(
            rows[0]
        )

    # -----------------------------------------------------
    # PENDING
    # -----------------------------------------------------

    response = (
        client
        .table(
            JOB_TABLE
        )
        .select(
            select_fields
        )
        .eq(
            "job_type",
            "connect",
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

    rows = list(
        response.data
        or []
    )

    if rows:
        return _normalize_job(
            rows[0]
        )

    # -----------------------------------------------------
    # LATEST
    # -----------------------------------------------------

    response = (
        client
        .table(
            JOB_TABLE
        )
        .select(
            select_fields
        )
        .eq(
            "job_type",
            "connect",
        )
        .order(
            "created_at",
            desc=True,
        )
        .limit(
            1
        )
        .execute()
    )

    rows = list(
        response.data
        or []
    )

    if not rows:
        return None

    return _normalize_job(
        rows[0]
    )


# =========================================================
# RECENT JOBS
# =========================================================


def get_recent_jobs(
    *,
    client: Client,
    limit: int = 10,
) -> list[dict]:
    response = (
        client
        .table(
            JOB_TABLE
        )
        .select(
            (
                "id,"
                "job_code,"
                "job_type,"
                "status,"
                "input_count,"
                "target_count,"
                "duplicate_count,"
                "invalid_count,"
                "processed_count,"
                "success_count,"
                "failed_count,"
                "last_error,"
                "created_at,"
                "started_at,"
                "completed_at,"
                "updated_at"
            )
        )
        .eq(
            "job_type",
            "connect",
        )
        .order(
            "created_at",
            desc=True,
        )
        .limit(
            limit
        )
        .execute()
    )

    rows = list(
        response.data
        or []
    )

    return [
        _normalize_job(
            row
        )
        for row in rows
    ]


# =========================================================
# SCHEDULER
# =========================================================


def get_scheduler_state(
    *,
    client: Client,
) -> dict | None:
    response = (
        client
        .table(
            SCHEDULER_TABLE
        )
        .select(
            (
                "scheduler_name,"
                "current_account_id,"
                "used_in_current_turn,"
                "turn_limit,"
                "updated_at"
            )
        )
        .eq(
            "scheduler_name",
            SCHEDULER_NAME,
        )
        .limit(
            1
        )
        .execute()
    )

    rows = list(
        response.data
        or []
    )

    if not rows:
        return None

    row = rows[0]

    used = _to_int(
        row.get(
            "used_in_current_turn"
        )
    )

    turn_limit = _to_int(
        row.get(
            "turn_limit"
        )
    )

    return {
        "scheduler_name": str(
            row.get(
                "scheduler_name",
                "",
            )
            or ""
        ),

        "current_account_id": str(
            row.get(
                "current_account_id",
                "",
            )
            or ""
        ),

        "used_in_current_turn": (
            used
        ),

        "turn_limit": (
            turn_limit
        ),

        "remaining_in_current_turn": max(
            turn_limit - used,
            0,
        ),

        "updated_at": (
            row.get(
                "updated_at"
            )
        ),
    }


# =========================================================
# ACCOUNTS
# =========================================================


def get_accounts(
    *,
    client: Client,
) -> list[dict]:
    response = (
        client
        .table(
            ACCOUNT_TABLE
        )
        .select(
            (
                "account_id,"
                "status,"
                "profile_directory,"
                "created_at,"
                "updated_at"
            )
        )
        .order(
            "account_id",
            desc=False,
        )
        .execute()
    )

    rows = list(
        response.data
        or []
    )

    return [
        {
            "account_id": str(
                row.get(
                    "account_id",
                    "",
                )
                or ""
            ),

            "status": str(
                row.get(
                    "status",
                    "",
                )
                or ""
            ),

            "profile_directory": str(
                row.get(
                    "profile_directory",
                    "",
                )
                or ""
            ),

            "created_at": (
                row.get(
                    "created_at"
                )
            ),

            "updated_at": (
                row.get(
                    "updated_at"
                )
            ),
        }
        for row in rows
    ]


# =========================================================
# DASHBOARD
# =========================================================


def get_outreach_dashboard(
    *,
    settings: Settings | None = None,
) -> dict:
    client = get_outreach_client(
        settings
    )

    return {
        "current_job": get_current_job(
            client=client
        ),

        "scheduler": get_scheduler_state(
            client=client
        ),

        "accounts": get_accounts(
            client=client
        ),

        "recent_jobs": get_recent_jobs(
            client=client,
            limit=10,
        ),
    }
