from __future__ import annotations

import os
import socket
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from app.linkedin_scanner import (
    create_supabase_client,
)
from app.settings import Settings


WORKER_TABLE = "scanner_workers"


WorkerType = Literal[
    "linkedin",
    "youtube",
]

WorkerStatus = Literal[
    "starting",
    "idle",
    "busy",
    "paused",
    "stopping",
    "offline",
    "error",
]


def _utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


@dataclass(frozen=True)
class WorkerRegistration:
    """
    Thông tin cơ bản mà mọi worker phải cung cấp.
    """

    worker_id: str
    worker_name: str
    worker_type: WorkerType

    capabilities: tuple[str, ...] = field(
        default_factory=tuple
    )

    max_concurrent_jobs: int = 1

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        worker_id = str(
            self.worker_id or ""
        ).strip()

        worker_name = str(
            self.worker_name or ""
        ).strip()

        if not worker_id:
            raise ValueError(
                "worker_id cannot be empty"
            )

        if not worker_name:
            raise ValueError(
                "worker_name cannot be empty"
            )

        if self.worker_type not in {
            "linkedin",
            "youtube",
        }:
            raise ValueError(
                "worker_type must be "
                "linkedin or youtube"
            )

        if self.max_concurrent_jobs < 1:
            raise ValueError(
                "max_concurrent_jobs "
                "must be at least 1"
            )

        cleaned_capabilities = tuple(
            str(capability).strip()
            for capability in self.capabilities
            if str(capability).strip()
        )

        object.__setattr__(
            self,
            "worker_id",
            worker_id,
        )

        object.__setattr__(
            self,
            "worker_name",
            worker_name,
        )

        object.__setattr__(
            self,
            "capabilities",
            cleaned_capabilities,
        )

    def supports(
        self,
        capability: str,
    ) -> bool:
        cleaned_capability = str(
            capability or ""
        ).strip()

        if not cleaned_capability:
            return False

        return (
            cleaned_capability
            in self.capabilities
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "worker_name": self.worker_name,
            "worker_type": self.worker_type,
            "capabilities": list(
                self.capabilities
            ),
            "max_concurrent_jobs": (
                self.max_concurrent_jobs
            ),
            "metadata": dict(
                self.metadata
            ),
        }


class WorkerRegistry:
    """
    Đăng ký worker vào bảng scanner_workers.
    """

    def __init__(
        self,
        *,
        settings: Settings,
    ) -> None:
        self.settings = settings

        self.client = create_supabase_client(
            settings
        )

        self.hostname = socket.gethostname()
        self.pid = os.getpid()

    def register(
        self,
        *,
        worker: WorkerRegistration,
        status: WorkerStatus = "starting",
        worker_version: str | None = None,
    ) -> dict[str, Any]:
        """
        Tạo hoặc cập nhật worker trong Supabase.
        """

        now = _utc_now_iso()

        payload = {
            **worker.to_dict(),
            "status": status,
            "current_job_id": None,
            "current_load": 0,
            "hostname": self.hostname,
            "pid": self.pid,
            "worker_version": (
                str(worker_version).strip()
                if worker_version
                else None
            ),
            "last_heartbeat_at": now,
            "started_at": now,
            "last_error": None,
            "last_error_at": None,
            "updated_at": now,
        }

        response = (
            self.client
            .table(WORKER_TABLE)
            .upsert(
                payload,
                on_conflict="worker_id",
            )
            .execute()
        )

        rows = list(
            response.data or []
        )

        if not rows:
            raise RuntimeError(
                "Supabase returned no worker row"
            )

        return dict(rows[0])
