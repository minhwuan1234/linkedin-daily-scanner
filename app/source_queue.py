from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.linkedin_scanner import (
    create_supabase_client,
)
from app.settings import Settings


SOURCE_TABLE = "linkedin_sources"
CLAIM_FUNCTION = "claim_linkedin_sources"
RELEASE_STALE_FUNCTION = (
    "release_stale_linkedin_jobs"
)

MAX_SOURCES_PER_CLAIM = 10
DEFAULT_MAX_RETRIES = 3


@dataclass(frozen=True)
class QueueSource:
    """
    Một LinkedIn source đã được account claim.

    Dữ liệu vẫn nằm trong bảng linkedin_sources chung.
    """

    id: int
    linkedin_url: str
    name: str | None
    source_type: str
    lark_chat_id: str | None
    lark_message_id: str | None
    lark_sender_open_id: str | None
    assigned_account_id: str | None
    retry_count: int

    @classmethod
    def from_row(
        cls,
        row: dict[str, Any],
    ) -> "QueueSource":
        source_id_raw = row.get("id")

        if source_id_raw is None:
            raise ValueError(
                "Queue source row is missing id"
            )

        linkedin_url = str(
            row.get("linkedin_url") or ""
        ).strip()

        if not linkedin_url:
            raise ValueError(
                "Queue source row is missing "
                "linkedin_url"
            )

        return cls(
            id=int(source_id_raw),
            linkedin_url=linkedin_url,
            name=_optional_text(
                row.get("name")
            ),
            source_type=(
                _optional_text(
                    row.get("source_type")
                )
                or "profile"
            ),
            lark_chat_id=_optional_text(
                row.get("lark_chat_id")
            ),
            lark_message_id=_optional_text(
                row.get("lark_message_id")
            ),
            lark_sender_open_id=(
                _optional_text(
                    row.get(
                        "lark_sender_open_id"
                    )
                )
            ),
            assigned_account_id=(
                _optional_text(
                    row.get(
                        "assigned_account_id"
                    )
                )
            ),
            retry_count=_safe_int(
                row.get("retry_count"),
                default=0,
            ),
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "id": self.id,
            "linkedin_url": self.linkedin_url,
            "name": self.name,
            "source_type": self.source_type,
            "lark_chat_id": self.lark_chat_id,
            "lark_message_id": (
                self.lark_message_id
            ),
            "lark_sender_open_id": (
                self.lark_sender_open_id
            ),
            "assigned_account_id": (
                self.assigned_account_id
            ),
            "retry_count": self.retry_count,
        }


def _optional_text(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    return text or None


def _safe_int(
    value: Any,
    *,
    default: int,
) -> int:
    try:
        return int(value)
    except (
        TypeError,
        ValueError,
    ):
        return default


def _utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


class LinkedInSourceQueue:
    """
    Quản lý queue chung trong Supabase.

    File này không mở browser.
    File này không scan LinkedIn.
    File này không tạo database mới.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        if max_retries < 1:
            raise ValueError(
                "max_retries must be at least 1"
            )

        self.settings = settings
        self.max_retries = max_retries
        self.client = create_supabase_client(
            settings
        )

    def claim_sources(
        self,
        *,
        account_id: str,
        limit: int,
    ) -> list[QueueSource]:
        """
        Claim tối đa 10 source pending cho một account.

        Database function dùng row locking nên account khác
        không thể claim cùng source trong cùng thời điểm.
        """
        cleaned_account_id = str(
            account_id or ""
        ).strip()

        if not cleaned_account_id:
            raise ValueError(
                "account_id cannot be empty"
            )

        resolved_limit = int(limit)

        if resolved_limit < 1:
            raise ValueError(
                "limit must be at least 1"
            )

        if resolved_limit > MAX_SOURCES_PER_CLAIM:
            raise ValueError(
                "limit cannot exceed "
                f"{MAX_SOURCES_PER_CLAIM}"
            )

        response = (
            self.client
            .rpc(
                CLAIM_FUNCTION,
                {
                    "p_account_id": (
                        cleaned_account_id
                    ),
                    "p_limit": resolved_limit,
                },
            )
            .execute()
        )

        rows = list(
            response.data or []
        )

        sources: list[QueueSource] = []

        for row in rows:
            if not isinstance(row, dict):
                continue

            source = QueueSource.from_row(
                row
            )

            if (
                source.assigned_account_id
                != cleaned_account_id
            ):
                raise RuntimeError(
                    "Claimed source was assigned "
                    "to an unexpected account. "
                    f"Expected {cleaned_account_id}, "
                    f"received "
                    f"{source.assigned_account_id}."
                )

            sources.append(source)

        return sources

    def heartbeat_source(
        self,
        *,
        source_id: int,
        account_id: str,
    ) -> None:
        """
        Update heartbeat trong lúc một source đang scan.

        Nếu scan dài, job sẽ không bị coi là stale.
        """
        response = (
            self.client
            .table(SOURCE_TABLE)
            .update(
                {
                    "processing_heartbeat_at": (
                        _utc_now_iso()
                    ),
                }
            )
            .eq(
                "id",
                int(source_id),
            )
            .eq(
                "job_status",
                "processing",
            )
            .eq(
                "assigned_account_id",
                str(account_id),
            )
            .execute()
        )

        rows = list(
            response.data or []
        )

        if not rows:
            raise RuntimeError(
                "Could not update source heartbeat. "
                f"source_id={source_id}, "
                f"account_id={account_id}"
            )

    def complete_source(
        self,
        *,
        source_id: int,
        account_id: str,
        scanned_at: str,
    ) -> None:
        """
        Đánh dấu source đã hoàn thành.

        Chỉ complete source đang processing và đang được
        account hiện tại giữ.
        """
        cleaned_scanned_at = str(
            scanned_at or ""
        ).strip()

        if not cleaned_scanned_at:
            raise ValueError(
                "scanned_at cannot be empty"
            )

        response = (
            self.client
            .table(SOURCE_TABLE)
            .update(
                {
                    "job_status": "completed",
                    "last_scanned_at": (
                        cleaned_scanned_at
                    ),
                    "completed_at": (
                        cleaned_scanned_at
                    ),
                    "processing_heartbeat_at": (
                        _utc_now_iso()
                    ),
                    "last_error": None,
                }
            )
            .eq(
                "id",
                int(source_id),
            )
            .eq(
                "job_status",
                "processing",
            )
            .eq(
                "assigned_account_id",
                str(account_id),
            )
            .execute()
        )

        rows = list(
            response.data or []
        )

        if not rows:
            raise RuntimeError(
                "Could not complete source. "
                f"source_id={source_id}, "
                f"account_id={account_id}"
            )

    def fail_source(
        self,
        *,
        source_id: int,
        account_id: str,
        error: Exception | str,
        retryable: bool = True,
    ) -> str:
        """
        Ghi nhận source scan lỗi.

        Nếu retryable và chưa quá max_retries:
            processing → pending

        Nếu không retryable hoặc đã quá giới hạn:
            processing → failed

        Trả về trạng thái mới.
        """
        source_row = self.get_source(
            source_id=source_id
        )

        current_retry_count = _safe_int(
            source_row.get("retry_count"),
            default=0,
        )

        next_retry_count = (
            current_retry_count + 1
        )

        should_retry = (
            retryable
            and next_retry_count
            < self.max_retries
        )

        next_status = (
            "pending"
            if should_retry
            else "failed"
        )

        error_text = (
            str(error or "Unknown error")
            .strip()[:4000]
        )

        update_payload: dict[str, Any] = {
            "job_status": next_status,
            "retry_count": next_retry_count,
            "last_error": error_text,
            "processing_heartbeat_at": (
                _utc_now_iso()
            ),
        }

        if should_retry:
            update_payload.update(
                {
                    "assigned_account_id": None,
                    "processing_started_at": None,
                    "processing_heartbeat_at": None,
                }
            )

        response = (
            self.client
            .table(SOURCE_TABLE)
            .update(update_payload)
            .eq(
                "id",
                int(source_id),
            )
            .eq(
                "job_status",
                "processing",
            )
            .eq(
                "assigned_account_id",
                str(account_id),
            )
            .execute()
        )

        rows = list(
            response.data or []
        )

        if not rows:
            raise RuntimeError(
                "Could not fail or release source. "
                f"source_id={source_id}, "
                f"account_id={account_id}"
            )

        return next_status

    def release_account_sources(
        self,
        *,
        account_id: str,
        reason: str,
    ) -> int:
        """
        Trả tất cả source processing của account về pending.

        Dùng khi account gặp login/checkpoint giữa batch.
        """
        cleaned_account_id = str(
            account_id or ""
        ).strip()

        if not cleaned_account_id:
            raise ValueError(
                "account_id cannot be empty"
            )

        error_text = str(
            reason or "Account batch released"
        ).strip()[:4000]

        response = (
            self.client
            .table(SOURCE_TABLE)
            .update(
                {
                    "job_status": "pending",
                    "assigned_account_id": None,
                    "processing_started_at": None,
                    "processing_heartbeat_at": None,
                    "last_error": error_text,
                }
            )
            .eq(
                "job_status",
                "processing",
            )
            .eq(
                "assigned_account_id",
                cleaned_account_id,
            )
            .execute()
        )

        return len(
            list(response.data or [])
        )

    def release_stale_sources(
        self,
        *,
        stale_after_minutes: int = 20,
    ) -> int:
        """
        Tự trả các job processing bị treo về pending.

        Ví dụ:
        - Mac reset.
        - Browser crash.
        - Worker bị kill giữa lúc scan.
        """
        resolved_minutes = int(
            stale_after_minutes
        )

        if resolved_minutes < 1:
            raise ValueError(
                "stale_after_minutes must be "
                "at least 1"
            )

        response = (
            self.client
            .rpc(
                RELEASE_STALE_FUNCTION,
                {
                    "p_stale_after_minutes": (
                        resolved_minutes
                    ),
                },
            )
            .execute()
        )

        data = response.data

        if isinstance(data, int):
            return data

        if isinstance(data, str):
            try:
                return int(data)
            except ValueError:
                return 0

        if isinstance(data, list) and data:
            first_value = data[0]

            if isinstance(first_value, int):
                return first_value

            if isinstance(first_value, dict):
                for value in (
                    first_value.values()
                ):
                    try:
                        return int(value)
                    except (
                        TypeError,
                        ValueError,
                    ):
                        continue

        return 0

    def get_source(
        self,
        *,
        source_id: int,
    ) -> dict[str, Any]:
        response = (
            self.client
            .table(SOURCE_TABLE)
            .select("*")
            .eq(
                "id",
                int(source_id),
            )
            .limit(1)
            .execute()
        )

        rows = list(
            response.data or []
        )

        if not rows:
            raise RuntimeError(
                "LinkedIn source not found: "
                f"{source_id}"
            )

        return dict(rows[0])

    def get_queue_counts(
        self,
    ) -> dict[str, int]:
        """
        Lấy thống kê queue phục vụ Terminal và health check.
        """
        statuses = (
            "pending",
            "processing",
            "completed",
            "failed",
            "disabled",
        )

        counts: dict[str, int] = {}

        for status in statuses:
            response = (
                self.client
                .table(SOURCE_TABLE)
                .select(
                    "id",
                    count="exact",
                )
                .eq(
                    "job_status",
                    status,
                )
                .limit(1)
                .execute()
            )

            counts[status] = int(
                response.count or 0
            )

        return counts
