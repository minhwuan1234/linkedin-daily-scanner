from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from supabase import Client, create_client

from app.settings import Settings


SCHEDULER_STATE_TABLE = (
    "outreach_scheduler_state"
)

DEFAULT_SCHEDULER_NAME = (
    "linkedin_outreach"
)


def _utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def create_outreach_supabase_client(
    settings: Settings,
) -> Client:
    """
    Tạo Supabase client dành riêng
    cho Outreach database.

    Không dùng Supabase scanner hiện tại.
    """

    return create_client(
        settings.outreach_supabase_url,
        settings.outreach_supabase_secret_key,
    )


@dataclass(frozen=True)
class OutreachSchedulerState:
    """
    State hiện tại của round-robin Outreach.
    """

    scheduler_name: str
    current_account_id: str
    used_in_current_turn: int
    turn_limit: int

    @property
    def remaining_in_current_turn(
        self,
    ) -> int:
        return max(
            self.turn_limit
            - self.used_in_current_turn,
            0,
        )

    @property
    def turn_is_complete(
        self,
    ) -> bool:
        return (
            self.used_in_current_turn
            >= self.turn_limit
        )


class OutreachSchedulerStateStore:
    """
    Đọc và ghi persistent round-robin state
    trong Supabase Outreach.

    Ví dụ:

    outreach_account_04
    used = 7
    limit = 10

    Worker restart vẫn có thể đọc lại 7/10.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        scheduler_name: str = (
            DEFAULT_SCHEDULER_NAME
        ),
    ) -> None:
        self.settings = settings

        self.scheduler_name = (
            str(
                scheduler_name
                or DEFAULT_SCHEDULER_NAME
            ).strip()
        )

        if not self.scheduler_name:
            raise ValueError(
                "scheduler_name is required"
            )

        self.client = (
            create_outreach_supabase_client(
                settings
            )
        )

    def load(
        self,
    ) -> OutreachSchedulerState:
        """
        Đọc state hiện tại từ Supabase.
        """

        response = (
            self.client
            .table(SCHEDULER_STATE_TABLE)
            .select(
                "scheduler_name,"
                "current_account_id,"
                "used_in_current_turn,"
                "turn_limit"
            )
            .eq(
                "scheduler_name",
                self.scheduler_name,
            )
            .limit(1)
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                "Outreach scheduler state "
                f"not found: {self.scheduler_name}"
            )

        row = response.data[0]

        current_account_id = str(
            row.get(
                "current_account_id"
            )
            or ""
        ).strip()

        if not current_account_id:
            raise RuntimeError(
                "Outreach scheduler state has "
                "no current_account_id"
            )

        used_in_current_turn = int(
            row.get(
                "used_in_current_turn"
            )
            or 0
        )

        turn_limit = int(
            row.get(
                "turn_limit"
            )
            or 10
        )

        if used_in_current_turn < 0:
            raise RuntimeError(
                "used_in_current_turn "
                "cannot be negative"
            )

        if turn_limit < 1:
            raise RuntimeError(
                "turn_limit must be at least 1"
            )

        return OutreachSchedulerState(
            scheduler_name=(
                self.scheduler_name
            ),
            current_account_id=(
                current_account_id
            ),
            used_in_current_turn=(
                used_in_current_turn
            ),
            turn_limit=turn_limit,
        )

    def save(
        self,
        *,
        current_account_id: str,
        used_in_current_turn: int,
        turn_limit: int,
    ) -> OutreachSchedulerState:
        """
        Ghi state mới vào Supabase.

        Dùng sau mỗi profile được xử lý
        để quota không bị mất nếu worker dừng.
        """

        cleaned_account_id = str(
            current_account_id or ""
        ).strip()

        if not cleaned_account_id:
            raise ValueError(
                "current_account_id is required"
            )

        used = int(
            used_in_current_turn
        )

        limit = int(
            turn_limit
        )

        if used < 0:
            raise ValueError(
                "used_in_current_turn "
                "cannot be negative"
            )

        if limit < 1:
            raise ValueError(
                "turn_limit must be at least 1"
            )

        if used > limit:
            raise ValueError(
                "used_in_current_turn "
                "cannot exceed turn_limit"
            )

        payload = {
            "scheduler_name": (
                self.scheduler_name
            ),
            "current_account_id": (
                cleaned_account_id
            ),
            "used_in_current_turn": used,
            "turn_limit": limit,
            "updated_at": _utc_now_iso(),
        }

        (
            self.client
            .table(SCHEDULER_STATE_TABLE)
            .upsert(
                payload,
                on_conflict="scheduler_name",
            )
            .execute()
        )

        return OutreachSchedulerState(
            scheduler_name=(
                self.scheduler_name
            ),
            current_account_id=(
                cleaned_account_id
            ),
            used_in_current_turn=used,
            turn_limit=limit,
        )

    def increment_usage(
        self,
        *,
        amount: int = 1,
    ) -> OutreachSchedulerState:
        """
        Tăng số profile đã dùng
        trong turn hiện tại.

        Ví dụ:
        7/10 -> 8/10
        """

        increment = int(amount)

        if increment < 1:
            raise ValueError(
                "amount must be at least 1"
            )

        state = self.load()

        new_used = (
            state.used_in_current_turn
            + increment
        )

        if new_used > state.turn_limit:
            raise RuntimeError(
                "Outreach account turn limit "
                "would be exceeded"
            )

        return self.save(
            current_account_id=(
                state.current_account_id
            ),
            used_in_current_turn=new_used,
            turn_limit=state.turn_limit,
        )

    def move_to_account(
        self,
        *,
        account_id: str,
        turn_limit: int,
    ) -> OutreachSchedulerState:
        """
        Chuyển sang account tiếp theo
        và reset quota về 0.

        Ví dụ:

        account_04 = 10/10
        ->
        account_05 = 0/10
        """

        return self.save(
            current_account_id=account_id,
            used_in_current_turn=0,
            turn_limit=turn_limit,
        )
