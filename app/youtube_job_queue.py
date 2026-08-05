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
        timezone.utc
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
            row.get("id") or ""
        ).strip()

        keyword = str(
            row.get("keyword") or ""
        ).strip()

        if not job_id:
            raise ValueError(
                "YouTube job is missing id"
            )

        if not keyword:
            raise ValueError(
                "YouTube job is missing keyword"
            )

        filters = row.get("filters")

        if not isinstance(filters, dict):
            filters = {}

        return cls(
            id=job_id,
            keyword=keyword,
            max_results=int(
                row.get("max_results") or 40
            ),
            filters=filters,
            retry_count=int(
                row.get("retry_count") or 0
            ),
            max_retries=int(
                row.get("max_retries") or 3
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
            settings
        )

    def claim_next_job(
        self,
        *,
        worker_id: str,
    ) -> YouTubeScanJob | None:
        cleaned_worker_id = str(
            worker_id or ""
        ).strip()

        if not cleaned_worker_id:
            raise ValueError(
                "worker_id cannot be empty"
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
            response.data or []
        )

        if not rows:
            return None

        candidate = dict(
            rows[0]
        )

        job_id = str(
            candidate.get("id") or ""
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
                    "assigned_worker_id": (
                        cleaned_worker_id
                    ),
                    "processing_started_at": now,
                    "processing_heartbeat_at": now,
                    "updated_at": now,
                    "last_error": None,
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

        claimed_rows = list(
            claim_response.data or []
        )

        if not claimed_rows:
            return None

        return YouTubeScanJob.from_row(
            dict(claimed_rows[0])
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
                    "current_stage": (
                        str(current_stage).strip()
                    ),
                    "progress_percent": max(
                        0,
                        min(
                            100,
                            int(progress_percent),
                        ),
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

        if not list(response.data or []):
            raise RuntimeError(
                "Could not update YouTube job heartbeat"
            )

            def release_job(
        self,
        *,
        job_id: str,
        worker_id: str,
        reason: str,
    ) -> None:
        """
        Trả job đang processing về pending.
        """

        cleaned_job_id = str(
            job_id or ""
        ).strip()

        cleaned_worker_id = str(
            worker_id or ""
        ).strip()

        if not cleaned_job_id:
            raise ValueError(
                "job_id cannot be empty"
            )

        if not cleaned_worker_id:
            raise ValueError(
                "worker_id cannot be empty"
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
                        reason or "Job released"
                    ).strip()[:4000],
                    "updated_at": now,
                }
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
                "Could not release YouTube job"
            )
