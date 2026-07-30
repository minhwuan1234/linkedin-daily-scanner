from __future__ import annotations

import os
import socket
from datetime import datetime, timezone
from typing import Any

from app.linkedin_scanner import create_supabase_client
from app.settings import Settings


WORKER_HEALTH_TABLE = "linkedin_worker_health"
ACCOUNT_TABLE = "linkedin_scanner_accounts"

DEFAULT_WORKER_ID = "mac_worker_01"
DEFAULT_WORKER_NAME = "LinkedIn Mac Worker"


def _utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def _optional_text(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    return text or None


class LinkedInWorkerHealth:
    """
    Ghi heartbeat của Mac worker và trạng thái 5 account
    vào cùng Supabase database hiện tại.

    File này không scan LinkedIn.
    File này không tạo browser.
    File này không gửi message Lark.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        worker_id: str | None = None,
        worker_name: str | None = None,
        worker_version: str | None = None,
    ) -> None:
        self.client = create_supabase_client(
            settings
        )

        self.worker_id = (
            _optional_text(worker_id)
            or _optional_text(
                os.getenv("LINKEDIN_WORKER_ID")
            )
            or DEFAULT_WORKER_ID
        )

        self.worker_name = (
            _optional_text(worker_name)
            or _optional_text(
                os.getenv("LINKEDIN_WORKER_NAME")
            )
            or DEFAULT_WORKER_NAME
        )

        self.worker_version = (
            _optional_text(worker_version)
            or _optional_text(
                os.getenv(
                    "LINKEDIN_WORKER_VERSION"
                )
            )
        )

        self.hostname = socket.gethostname()
        self.pid = os.getpid()

    def register_worker(
        self,
        *,
        status: str = "starting",
    ) -> None:
        now = _utc_now_iso()

        payload = {
            "worker_id": self.worker_id,
            "worker_name": self.worker_name,
            "status": status,
            "worker_version": (
                self.worker_version
            ),
            "hostname": self.hostname,
            "pid": self.pid,
            "current_account_id": None,
            "current_source_id": None,
            "last_heartbeat_at": now,
            "started_at": now,
            "last_error": None,
            "last_error_at": None,
            "updated_at": now,
        }

        (
            self.client
            .table(WORKER_HEALTH_TABLE)
            .upsert(
                payload,
                on_conflict="worker_id",
            )
            .execute()
        )

    def touch_heartbeat(
        self,
        *,
        status: str | None = None,
        current_account_id: str | None = None,
        current_source_id: int | None = None,
    ) -> None:
        """
        Refresh only the live heartbeat fields.

        This method deliberately does not clear last_error,
        last_error_at, last_success_at, or batch timestamps.
        It is safe for a background heartbeat thread.
        """
        now = _utc_now_iso()

        payload: dict[str, Any] = {
            "hostname": self.hostname,
            "pid": self.pid,
            "worker_version": self.worker_version,
            "last_heartbeat_at": now,
            "updated_at": now,
        }

        if status is not None:
            payload["status"] = status

        payload["current_account_id"] = current_account_id
        payload["current_source_id"] = (
            int(current_source_id)
            if current_source_id is not None
            else None
        )

        response = (
            self.client
            .table(WORKER_HEALTH_TABLE)
            .update(payload)
            .eq(
                "worker_id",
                self.worker_id,
            )
            .execute()
        )

        if not list(response.data or []):
            self.register_worker(
                status=status or "starting"
            )

    def heartbeat(
        self,
        *,
        status: str,
        current_account_id: str | None = None,
        current_source_id: int | None = None,
        last_error: str | None = None,
    ) -> None:
        now = _utc_now_iso()

        payload: dict[str, Any] = {
            "status": status,
            "hostname": self.hostname,
            "pid": self.pid,
            "worker_version": (
                self.worker_version
            ),
            "current_account_id": (
                current_account_id
            ),
            "current_source_id": (
                int(current_source_id)
                if current_source_id is not None
                else None
            ),
            "last_heartbeat_at": now,
            "updated_at": now,
        }

        if last_error:
            payload["last_error"] = (
                str(last_error)[:4000]
            )
            payload["last_error_at"] = now
        else:
            payload["last_error"] = None

        response = (
            self.client
            .table(WORKER_HEALTH_TABLE)
            .update(payload)
            .eq(
                "worker_id",
                self.worker_id,
            )
            .execute()
        )

        if not list(response.data or []):
            self.register_worker(
                status=status
            )

    def mark_batch_started(
        self,
        *,
        account_id: str,
    ) -> None:
        now = _utc_now_iso()

        (
            self.client
            .table(WORKER_HEALTH_TABLE)
            .update(
                {
                    "status": "scanning",
                    "current_account_id": (
                        account_id
                    ),
                    "current_source_id": None,
                    "last_batch_started_at": now,
                    "last_heartbeat_at": now,
                    "updated_at": now,
                }
            )
            .eq(
                "worker_id",
                self.worker_id,
            )
            .execute()
        )

    def mark_batch_completed(
        self,
    ) -> None:
        now = _utc_now_iso()

        (
            self.client
            .table(WORKER_HEALTH_TABLE)
            .update(
                {
                    "status": "idle",
                    "current_account_id": None,
                    "current_source_id": None,
                    "last_batch_completed_at": now,
                    "last_heartbeat_at": now,
                    "updated_at": now,
                }
            )
            .eq(
                "worker_id",
                self.worker_id,
            )
            .execute()
        )

    def mark_success(
        self,
        *,
        account_id: str,
        source_id: int,
    ) -> None:
        now = _utc_now_iso()

        (
            self.client
            .table(WORKER_HEALTH_TABLE)
            .update(
                {
                    "status": "scanning",
                    "current_account_id": (
                        account_id
                    ),
                    "current_source_id": (
                        int(source_id)
                    ),
                    "last_success_at": now,
                    "last_heartbeat_at": now,
                    "last_error": None,
                    "updated_at": now,
                }
            )
            .eq(
                "worker_id",
                self.worker_id,
            )
            .execute()
        )

    def mark_error(
        self,
        *,
        error: Exception | str,
        account_id: str | None = None,
        source_id: int | None = None,
    ) -> None:
        self.heartbeat(
            status="error",
            current_account_id=account_id,
            current_source_id=source_id,
            last_error=(
                f"{type(error).__name__}: {error}"
                if isinstance(error, Exception)
                else str(error)
            ),
        )

    def mark_stopping(
        self,
    ) -> None:
        self.heartbeat(
            status="stopping",
            current_account_id=None,
            current_source_id=None,
        )

    def set_account_status(
        self,
        *,
        account_id: str,
        status: str,
        current_source_id: int | None = None,
        last_error: str | None = None,
        increment_failure: bool = False,
        reset_failure: bool = False,
    ) -> None:
        now = _utc_now_iso()

        account_response = (
            self.client
            .table(ACCOUNT_TABLE)
            .select(
                "consecutive_failures"
            )
            .eq(
                "account_id",
                account_id,
            )
            .limit(1)
            .execute()
        )

        rows = list(
            account_response.data or []
        )

        current_failures = 0

        if rows:
            try:
                current_failures = int(
                    rows[0].get(
                        "consecutive_failures",
                        0,
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                current_failures = 0

        if reset_failure:
            next_failures = 0
        elif increment_failure:
            next_failures = (
                current_failures + 1
            )
        else:
            next_failures = current_failures

        payload: dict[str, Any] = {
            "status": status,
            "current_source_id": (
                int(current_source_id)
                if current_source_id is not None
                else None
            ),
            "consecutive_failures": (
                next_failures
            ),
            "updated_at": now,
        }

        if status == "scanning":
            payload["last_used_at"] = now

        if status == "available":
            payload["cooldown_until"] = None

        if last_error:
            payload["last_error"] = (
                str(last_error)[:4000]
            )
            payload["last_error_at"] = now
        elif reset_failure:
            payload["last_error"] = None

        response = (
            self.client
            .table(ACCOUNT_TABLE)
            .update(payload)
            .eq(
                "account_id",
                account_id,
            )
            .execute()
        )

        if not list(response.data or []):
            raise RuntimeError(
                "LinkedIn account status row "
                f"not found: {account_id}"
            )

    def mark_account_scanning(
        self,
        *,
        account_id: str,
        source_id: int | None = None,
    ) -> None:
        self.set_account_status(
            account_id=account_id,
            status="scanning",
            current_source_id=source_id,
        )

    def mark_account_available(
        self,
        *,
        account_id: str,
        success: bool = False,
    ) -> None:
        now = _utc_now_iso()

        self.set_account_status(
            account_id=account_id,
            status="available",
            current_source_id=None,
            reset_failure=success,
        )

        if success:
            (
                self.client
                .table(ACCOUNT_TABLE)
                .update(
                    {
                        "last_success_at": now,
                        "updated_at": now,
                    }
                )
                .eq(
                    "account_id",
                    account_id,
                )
                .execute()
            )

    def mark_account_needs_login(
        self,
        *,
        account_id: str,
        error: Exception | str,
    ) -> None:
        error_text = (
            f"{type(error).__name__}: {error}"
            if isinstance(error, Exception)
            else str(error)
        )

        self.set_account_status(
            account_id=account_id,
            status="needs_login",
            current_source_id=None,
            last_error=error_text,
            increment_failure=True,
        )

    def mark_account_error(
        self,
        *,
        account_id: str,
        error: Exception | str,
        source_id: int | None = None,
    ) -> None:
        error_text = (
            f"{type(error).__name__}: {error}"
            if isinstance(error, Exception)
            else str(error)
        )

        self.set_account_status(
            account_id=account_id,
            status="error",
            current_source_id=source_id,
            last_error=error_text,
            increment_failure=True,
        )
