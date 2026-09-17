from __future__ import annotations

import json
import sys
from typing import Any

from app.linkedin_scanner import (
    create_supabase_client,
)
from app.settings import Settings


EVENT_TABLE = "scanner_job_events"


class JobEventStore:
    """
    Ghi timeline realtime cho mọi scanner job.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        worker_id: str,
        platform: str,
    ) -> None:
        cleaned_worker_id = str(
            worker_id or ""
        ).strip()

        cleaned_platform = str(
            platform or ""
        ).strip().lower()

        if not cleaned_worker_id:
            raise ValueError(
                "worker_id cannot be empty"
            )

        if cleaned_platform not in {
            "linkedin",
            "youtube",
        }:
            raise ValueError(
                "platform must be linkedin or youtube"
            )

        self.client = create_supabase_client(
            settings
        )

        self.worker_id = cleaned_worker_id
        self.platform = cleaned_platform

    def emit(
        self,
        *,
        job_id: str,
        event_type: str,
        step_name: str,
        status: str = "info",
        message: str | None = None,
        progress_percent: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        cleaned_job_id = str(
            job_id or ""
        ).strip()

        if not cleaned_job_id:
            raise ValueError(
                "job_id cannot be empty"
            )

        payload = {
            "job_id": cleaned_job_id,
            "worker_id": self.worker_id,
            "platform": self.platform,
            "event_type": self._clean_required(
                event_type,
                field_name="event_type",
            ),
            "step_name": self._clean_required(
                step_name,
                field_name="step_name",
            ),
            "status": self._normalise_status(
                status
            ),
            "message": (
                str(message).strip()[:4000]
                if message
                else None
            ),
            "progress_percent": (
                self._normalise_progress(
                    progress_percent
                )
            ),
            "metadata": self._safe_metadata(
                metadata
            ),
        }

        try:
            response = (
                self.client
                .table(EVENT_TABLE)
                .insert(payload)
                .execute()
            )

            return bool(
                response.data
            )

        except Exception as exc:
            print(
                "Could not write job event: "
                f"{type(exc).__name__}: {exc}",
                file=sys.stderr,
            )

            return False

    @staticmethod
    def _clean_required(
        value: str,
        *,
        field_name: str,
    ) -> str:
        cleaned = str(
            value or ""
        ).strip()

        if not cleaned:
            raise ValueError(
                f"{field_name} is required"
            )

        return cleaned[:120]

    @staticmethod
    def _normalise_status(
        value: str,
    ) -> str:
        cleaned = str(
            value or "info"
        ).strip().lower()

        allowed = {
            "info",
            "queued",
            "processing",
            "success",
            "warning",
            "error",
        }

        return (
            cleaned
            if cleaned in allowed
            else "info"
        )

    @staticmethod
    def _normalise_progress(
        value: int | None,
    ) -> int | None:
        if value is None:
            return None

        return max(
            0,
            min(
                100,
                int(value),
            ),
        )

    @staticmethod
    def _safe_metadata(
        value: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not value:
            return {}

        try:
            serialised = json.dumps(
                value,
                ensure_ascii=False,
                default=str,
            )

            decoded = json.loads(
                serialised
            )

        except Exception:
            return {}

        return (
            decoded
            if isinstance(decoded, dict)
            else {}
        )
