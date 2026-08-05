
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


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


@dataclass(frozen=True)
class WorkerRegistration:
    """
    Thông tin cơ bản mà mọi worker phải cung cấp
    khi đăng ký với hệ thống điều phối.
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
        worker_id = self.worker_id.strip()
        worker_name = self.worker_name.strip()

        if not worker_id:
            raise ValueError(
                "worker_id cannot be empty"
            )

        if not worker_name:
            raise ValueError(
                "worker_name cannot be empty"
            )

        if self.max_concurrent_jobs < 1:
            raise ValueError(
                "max_concurrent_jobs must be at least 1"
            )

        cleaned_capabilities = tuple(
            capability.strip()
            for capability in self.capabilities
            if capability.strip()
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
        """
        Kiểm tra worker có hỗ trợ một khả năng cụ thể hay không.
        """

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
        """
        Chuyển thông tin worker thành dictionary
        để sau này ghi vào Supabase.
        """

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
