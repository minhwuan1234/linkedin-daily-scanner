from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.linkedin_scanner import create_supabase_client
from app.settings import Settings


COMMAND_TABLE = "linkedin_worker_commands"


def _utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


@dataclass(frozen=True)
class WorkerCommand:
    id: int
    worker_id: str
    command: str

    @classmethod
    def from_row(
        cls,
        row: dict[str, Any],
    ) -> "WorkerCommand":
        return cls(
            id=int(row["id"]),
            worker_id=str(row["worker_id"]),
            command=str(row["command"]),
        )


class WorkerCommandStore:
    def __init__(
        self,
        *,
        settings: Settings,
        worker_id: str,
    ) -> None:
        self.client = create_supabase_client(
            settings
        )
        self.worker_id = str(worker_id).strip()

        if not self.worker_id:
            raise ValueError(
                "worker_id cannot be empty"
            )

    def claim_next_command(
        self,
    ) -> WorkerCommand | None:
        response = (
            self.client
            .table(COMMAND_TABLE)
            .select(
                "id,worker_id,command,status,requested_at"
            )
            .eq(
                "worker_id",
                self.worker_id,
            )
            .eq(
                "status",
                "pending",
            )
            .order(
                "requested_at",
                desc=False,
            )
            .limit(1)
            .execute()
        )

        rows = list(response.data or [])

        if not rows:
            return None

        row = rows[0]
        command_id = int(row["id"])

        update_response = (
            self.client
            .table(COMMAND_TABLE)
            .update(
                {
                    "status": "processing",
                    "error": None,
                }
            )
            .eq(
                "id",
                command_id,
            )
            .eq(
                "status",
                "pending",
            )
            .execute()
        )

        updated_rows = list(
            update_response.data or []
        )

        if not updated_rows:
            return None

        return WorkerCommand.from_row(
            updated_rows[0]
        )

    def complete(
        self,
        *,
        command_id: int,
    ) -> None:
        (
            self.client
            .table(COMMAND_TABLE)
            .update(
                {
                    "status": "completed",
                    "processed_at": (
                        _utc_now_iso()
                    ),
                    "error": None,
                }
            )
            .eq(
                "id",
                int(command_id),
            )
            .execute()
        )

    def fail(
        self,
        *,
        command_id: int,
        error: Exception | str,
    ) -> None:
        (
            self.client
            .table(COMMAND_TABLE)
            .update(
                {
                    "status": "failed",
                    "processed_at": (
                        _utc_now_iso()
                    ),
                    "error": str(error)[:2000],
                }
            )
            .eq(
                "id",
                int(command_id),
            )
            .execute()
        )
