from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from supabase import Client, create_client

from app.settings import (
    Settings,
    load_settings,
)


JOB_TABLE = "outreach_jobs"


class OutreachJobQueueError(
    RuntimeError
):
    pass


@dataclass(frozen=True)
class OutreachConnectJob:
    id: str
    job_code: str
    status: str

    input_count: int
    target_count: int
    duplicate_count: int

    processed_count: int
    success_count: int
    failed_count: int


# =========================================================
# HELPERS
# =========================================================


def _utc_now() -> str:
    return (
        datetime
        .now(timezone.utc)
        .isoformat()
    )


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


def _row_to_job(
    row: dict,
) -> OutreachConnectJob:
    return OutreachConnectJob(
        id=str(
            row.get(
                "id",
                "",
            )
        ),
        job_code=str(
            row.get(
                "job_code",
                "",
            )
            or ""
        ),
        status=str(
            row.get(
                "status",
                "",
            )
            or ""
        ),
        input_count=_to_int(
            row.get(
                "input_count"
            )
        ),
        target_count=_to_int(
            row.get(
                "target_count"
            )
        ),
        duplicate_count=_to_int(
            row.get(
                "duplicate_count"
            )
        ),
        processed_count=_to_int(
            row.get(
                "processed_count"
            )
        ),
        success_count=_to_int(
            row.get(
                "success_count"
            )
        ),
        failed_count=_to_int(
            row.get(
                "failed_count"
            )
        ),
    )


# =========================================================
# QUEUE
# =========================================================


class OutreachJobQueue:
    """
    Queue cho LinkedIn Outreach Connect jobs.

    Worker gọi:

        claim_next_job()

    Nếu có job pending:
        pending -> running

    Nếu không có:
        return None
    """

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: Client | None = None,
    ) -> None:
        self.settings = (
            settings
            if settings is not None
            else load_settings()
        )

        if client is not None:
            self.client = client
            return

        if not (
            self.settings
            .outreach_supabase_url
        ):
            raise OutreachJobQueueError(
                "Missing OUTREACH_SUPABASE_URL."
            )

        if not (
            self.settings
            .outreach_supabase_secret_key
        ):
            raise OutreachJobQueueError(
                "Missing "
                "OUTREACH_SUPABASE_SECRET_KEY."
            )

        self.client = create_client(
            self.settings
            .outreach_supabase_url,
            self.settings
            .outreach_supabase_secret_key,
        )

    # =====================================================
    # CLAIM
    # =====================================================

    def claim_next_job(
        self,
    ) -> OutreachConnectJob | None:
        """
        Lấy Connect job pending cũ nhất.

        Sau khi tìm thấy:
            status -> running
            started_at -> now

        V1 hiện có một Outreach worker,
        nên flow này đủ cho hiện tại.
        """

        response = (
            self.client
            .table(
                JOB_TABLE
            )
            .select(
                (
                    "id,"
                    "job_code,"
                    "status,"
                    "input_count,"
                    "target_count,"
                    "duplicate_count,"
                    "processed_count,"
                    "success_count,"
                    "failed_count,"
                    "created_at"
                )
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

        if not rows:
            return None

        row = rows[0]

        job_id = str(
            row["id"]
        )

        now = _utc_now()

        update_response = (
            self.client
            .table(
                JOB_TABLE
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
                job_id,
            )
            .eq(
                "status",
                "pending",
            )
            .execute()
        )

        updated_rows = list(
            update_response.data
            or []
        )

        # Có thể job vừa bị worker khác claim.
        if not updated_rows:
            return None

        updated = updated_rows[0]

        return _row_to_job(
            updated
        )

    # =====================================================
    # GET JOB
    # =====================================================

    def get_job(
        self,
        *,
        job_id: str,
    ) -> OutreachConnectJob:
        response = (
            self.client
            .table(
                JOB_TABLE
            )
            .select(
                (
                    "id,"
                    "job_code,"
                    "status,"
                    "input_count,"
                    "target_count,"
                    "duplicate_count,"
                    "processed_count,"
                    "success_count,"
                    "failed_count"
                )
            )
            .eq(
                "id",
                job_id,
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
            raise OutreachJobQueueError(
                "Outreach job not found: "
                f"{job_id}"
            )

        return _row_to_job(
            rows[0]
        )

    # =====================================================
    # COMPLETE
    # =====================================================

    def complete_job(
        self,
        *,
        job_id: str,
    ) -> None:
        """
        Đánh dấu job hoàn thành.

        Counters success/failed đã được
        outreach_result_store cập nhật
        sau mỗi profile.
        """

        now = _utc_now()

        (
            self.client
            .table(
                JOB_TABLE
            )
            .update(
                {
                    "status": "completed",
                    "completed_at": now,
                    "updated_at": now,
                    "last_error": None,
                }
            )
            .eq(
                "id",
                job_id,
            )
            .execute()
        )

    # =====================================================
    # FAIL
    # =====================================================

    def fail_job(
        self,
        *,
        job_id: str,
        error_message: str,
    ) -> None:
        """
        Dùng khi cả job bị lỗi ở cấp worker.

        Khác với:
            một profile FAILED

        Profile fail chỉ tăng failed_count
        và worker vẫn chạy tiếp.
        """

        now = _utc_now()

        (
            self.client
            .table(
                JOB_TABLE
            )
            .update(
                {
                    "status": "failed",
                    "last_error": str(
                        error_message
                        or ""
                    ),
                    "completed_at": now,
                    "updated_at": now,
                }
            )
            .eq(
                "id",
                job_id,
            )
            .execute()
        )
