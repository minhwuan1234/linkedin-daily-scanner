from __future__ import annotations

from dataclasses import dataclass

from app.outreach_account_pool import (
    OutreachAccount,
    OutreachAccountPool,
)
from app.outreach_scheduler_state import (
    OutreachSchedulerState,
    OutreachSchedulerStateStore,
)
from app.settings import Settings


@dataclass(frozen=True)
class OutreachAccountTurn:
    """
    Thông tin account đang được scheduler chọn.

    Ví dụ:

    outreach_account_04
    used = 7
    remaining = 3
    limit = 10
    """

    account: OutreachAccount

    used_in_current_turn: int
    remaining_in_current_turn: int
    turn_limit: int


class OutreachScheduler:
    """
    Persistent round-robin scheduler
    cho LinkedIn Outreach.

    Scheduler này chịu trách nhiệm:

    - đọc account hiện tại từ Supabase;
    - tính quota còn lại;
    - tăng quota sau mỗi profile;
    - chuyển sang account kế tiếp khi đủ turn_limit;
    - giữ state qua nhiều job và qua worker restart.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        account_pool: OutreachAccountPool | None = None,
        state_store: OutreachSchedulerStateStore | None = None,
    ) -> None:
        self.settings = settings

        self.account_pool = (
            account_pool
            if account_pool is not None
            else OutreachAccountPool()
        )

        self.state_store = (
            state_store
            if state_store is not None
            else OutreachSchedulerStateStore(
                settings=settings
            )
        )

    def load_state(
        self,
    ) -> OutreachSchedulerState:
        """
        Đọc scheduler state hiện tại.

        Đồng thời kiểm tra account đang lưu
        trong Supabase có thực sự tồn tại
        trong OutreachAccountPool hay không.
        """

        state = self.state_store.load()

        self.account_pool.get_account(
            state.current_account_id
        )

        return state

    def get_current_turn(
        self,
    ) -> OutreachAccountTurn:
        """
        Lấy account hiện tại cùng quota còn lại.

        Nếu state đang ở đúng 10/10
        thì scheduler tự chuyển sang account tiếp theo
        trước khi trả về.
        """

        state = self.load_state()

        if state.turn_is_complete:
            state = self.move_to_next_account(
                state=state
            )

        account = self.account_pool.get_account(
            state.current_account_id
        )

        return OutreachAccountTurn(
            account=account,
            used_in_current_turn=(
                state.used_in_current_turn
            ),
            remaining_in_current_turn=(
                state.remaining_in_current_turn
            ),
            turn_limit=state.turn_limit,
        )

    def record_profile_processed(
        self,
        *,
        amount: int = 1,
    ) -> OutreachSchedulerState:
        """
        Gọi sau khi một profile đã được account
        sử dụng cho một Connect attempt.

        Ví dụ:

        account_04 = 7/10
        -> xử lý 1 profile
        -> account_04 = 8/10

        Nếu thành 10/10 thì state vẫn được lưu 10/10.
        Lần get_current_turn() tiếp theo sẽ tự chuyển account.
        """

        return self.state_store.increment_usage(
            amount=amount
        )

    def move_to_next_account(
        self,
        *,
        state: OutreachSchedulerState | None = None,
    ) -> OutreachSchedulerState:
        """
        Chuyển persistent state sang account tiếp theo.

        Ví dụ:

        outreach_account_04 = 10/10
        ->
        outreach_account_05 = 0/10

        Nếu account_05 là cuối pool:
        ->
        outreach_account_01
        """

        current_state = (
            state
            if state is not None
            else self.load_state()
        )

        current_index = (
            self.account_pool
            .get_account_index(
                current_state.current_account_id
            )
        )

        next_index = (
            current_index + 1
        ) % len(
            self.account_pool.accounts
        )

        next_account = (
            self.account_pool
            .accounts[next_index]
        )

        return self.state_store.move_to_account(
            account_id=next_account.account_id,
            turn_limit=current_state.turn_limit,
        )

    def get_batch_capacity(
        self,
        *,
        requested_count: int,
    ) -> int:
        """
        Tính số target tối đa account hiện tại
        được phép nhận trong lượt này.

        Ví dụ:

        account_04 đang 7/10
        requested_count = 20

        result = 3
        """

        requested = int(
            requested_count
        )

        if requested < 0:
            raise ValueError(
                "requested_count cannot be negative"
            )

        if requested == 0:
            return 0

        turn = self.get_current_turn()

        return min(
            requested,
            turn.remaining_in_current_turn,
        )
