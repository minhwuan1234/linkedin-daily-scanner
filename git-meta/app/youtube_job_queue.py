from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.linkedin_scanner import (
    create_supabase_client,
)
from app.settings import Settings


JOB_TABLE = "youtube_scan_jobs"


def _utc_now_iso() -> str:
    return datetime.now(
        timezone.utc,
    ).isoformat()


@dataclass(frozen=True)
class YouTubeScanJob:
    id: str
    keyword: str
    max_results: int
    filters: dict[str, Any]
    retry_count: int
    max_retries: int

    @classmethod
    def from_row(
        cls,
        row: dict[str, Any],
    ) -> "YouTubeScanJob":
        job_id = str(
            row.get("id") or "",
        ).strip()

        keyword = str(
            row.get("keyword") or "",
        ).strip()

        if not job_id:
            raise ValueError(
                "YouTube job is missing id",
            )

        if not keyword:
            raise ValueError(
                "YouTube job is missing keyword",
            )

        filters = row.get("filters")

        if not isinstance(filters, dict):
            filters = {}

        return cls(
            id=job_id,
            keyword=keyword,
            max_results=int(
                row.get("max_results") or 40,
            ),
            filters=filters,
            retry_count=int(
                row.get("retry_count") or 0,
            ),
            max_retries=int(
                row.get("max_retries") or 3,
            ),
        )


class YouTubeJobQueue:
    """
    Quản lý queue job YouTube trong Supabase.
    """

    def __init__(
        self,
        *,
        settings: Settings,
    ) -> None:
        self.client = create_supabase_client(
            settings,
        )

    def claim_next_job(
        self,
        *,
        worker_id: str,
    ) -> YouTubeScanJob | None:
        cleaned_worker_id = str(
            worker_id or "",
        ).strip()

        if not cleaned_worker_id:
            raise ValueError(
                "worker_id cannot be empty",
            )

        response = (
            self.client
            .table(JOB_TABLE)
            .select("*")
            .eq(
                "status",
                "pending",
            )
            .order(
                "created_at",
            )
            .limit(1)
            .execute()
        )

        rows = list(
            response.data or [],
        )

        if not rows:
            return None

        candidate = dict(
            rows[0],
        )

        job_id = str(
            candidate.get("id") or "",
        ).strip()

        now = _utc_now_iso()

        claim_response = (
            self.client
            .table(JOB_TABLE)
            .update(
                {
                    "status": "processing",
                    "current_stage": "claimed",
                    "progress_percent": 5,
                    "assigned_worker_id": cleaned_worker_id,
                    "processing_started_at": now,
                    "processing_heartbeat_at": now,
                    "updated_at": now,
                    "last_error": None,
                },
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

        claimed_rows = list(
            claim_response.data or [],
        )

        if not claimed_rows:
            return None

        return YouTubeScanJob.from_row(
            dict(claimed_rows[0]),
        )

    def heartbeat_job(
        self,
        *,
        job_id: str,
        worker_id: str,
        current_stage: str,
        progress_percent: int,
    ) -> None:
        now = _utc_now_iso()

        response = (
            self.client
            .table(JOB_TABLE)
            .update(
                {
                    "current_stage": str(
                        current_stage,
                    ).strip(),
                    "progress_percent": max(
                        0,
                        min(
                            100,
                            int(progress_percent),
                        ),
                    ),
                    "processing_heartbeat_at": now,
                    "updated_at": now,
                },
            )
            .eq(
                "id",
                str(job_id),
            )
            .eq(
                "status",
                "processing",
            )
            .eq(
                "assigned_worker_id",
                str(worker_id),
            )
            .execute()
        )

        if not list(response.data or []):
            raise RuntimeError(
                "Could not update YouTube job heartbeat",
            )

    def update_result_progress(
        self,
        *,
        job_id: str,
        worker_id: str,
        current_stage: str,
        progress_percent: int,
        result_count: int,
    ) -> None:
        """
        Update progress and saved result count while scanning.
        """

        now = _utc_now_iso()

        response = (
            self.client
            .table(JOB_TABLE)
            .update(
                {
                    "current_stage": str(
                        current_stage
                    ).strip(),
                    "progress_percent": max(
                        0,
                        min(
                            100,
                            int(progress_percent),
                        ),
                    ),
                    "result_count": max(
                        0,
                        int(result_count),
                    ),
                    "processing_heartbeat_at": now,
                    "updated_at": now,
                }
            )
            .eq(
                "id",
                str(job_id),
            )
            .eq(
                "status",
                "processing",
            )
            .eq(
                "assigned_worker_id",
                str(worker_id),
            )
            .execute()
        )

        if not list(
            response.data or []
        ):
            raise RuntimeError(
                "Could not update YouTube result progress"
            )


    def complete_job(
        self,
        *,
        job_id: str,
        worker_id: str,
        result_count: int,
    ) -> None:
        now = _utc_now_iso()

        response = (
            self.client
            .table(JOB_TABLE)
            .update(
                {
                    "status": "completed",
                    "current_stage": "completed",
                    "progress_percent": 100,
                    "result_count": max(
                        0,
                        int(result_count),
                    ),
                    "processing_heartbeat_at": now,
                    "completed_at": now,
                    "updated_at": now,
                    "last_error": None,
                },
            )
            .eq(
                "id",
                str(job_id),
            )
            .eq(
                "status",
                "processing",
            )
            .eq(
                "assigned_worker_id",
                str(worker_id),
            )
            .execute()
        )

        if not list(response.data or []):
            raise RuntimeError(
                "Could not complete YouTube job",
            )

    def fail_job(
        self,
        *,
        job: YouTubeScanJob,
        worker_id: str,
        error_message: str,
    ) -> str:
        """
        Nếu còn retry:
        processing -> pending

        Nếu hết retry:
        processing -> failed

        Trả về trạng thái cuối: pending hoặc failed.
        """

        next_retry_count = (
            int(job.retry_count) + 1
        )

        should_retry = (
            next_retry_count
            <= int(job.max_retries)
        )

        next_status = (
            "pending"
            if should_retry
            else "failed"
        )

        now = _utc_now_iso()

        update_data: dict[str, Any] = {
            "status": next_status,
            "current_stage": (
                "queued"
                if should_retry
                else "failed"
            ),
            "progress_percent": (
                0
                if should_retry
                else 100
            ),
            "retry_count": next_retry_count,
            "assigned_worker_id": None,
            "processing_started_at": None,
            "processing_heartbeat_at": None,
            "last_error": str(
                error_message or "Unknown YouTube worker error",
            ).strip()[:4000],
            "updated_at": now,
        }

        if not should_retry:
            update_data["completed_at"] = now

        response = (
            self.client
            .table(JOB_TABLE)
            .update(
                update_data,
            )
            .eq(
                "id",
                str(job.id),
            )
            .eq(
                "status",
                "processing",
            )
            .eq(
                "assigned_worker_id",
                str(worker_id),
            )
            .execute()
        )

        if not list(response.data or []):
            raise RuntimeError(
                "Could not fail YouTube job",
            )

        return next_status

    def release_job(
        self,
        *,
        job_id: str,
        worker_id: str,
        reason: str,
    ) -> None:
        cleaned_job_id = str(
            job_id or "",
        ).strip()

        cleaned_worker_id = str(
            worker_id or "",
        ).strip()

        if not cleaned_job_id:
            raise ValueError(
                "job_id cannot be empty",
            )

        if not cleaned_worker_id:
            raise ValueError(
                "worker_id cannot be empty",
            )

        now = _utc_now_iso()

        response = (
            self.client
            .table(JOB_TABLE)
            .update(
                {
                    "status": "pending",
                    "current_stage": "queued",
                    "progress_percent": 0,
                    "assigned_worker_id": None,
                    "processing_started_at": None,
                    "processing_heartbeat_at": None,
                    "last_error": str(
                        reason or "Job released",
                    ).strip()[:4000],
                    "updated_at": now,
                },
            )
            .eq(
                "id",
                cleaned_job_id,
            )
            .eq(
                "status",
                "processing",
            )
            .eq(
                "assigned_worker_id",
                cleaned_worker_id,
            )
            .execute()
        )

        if not list(response.data or []):
            raise RuntimeError(
                "Could not release YouTube job",
            )
