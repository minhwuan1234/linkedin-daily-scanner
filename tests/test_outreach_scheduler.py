from __future__ import annotations

from dataclasses import dataclass

from app.outreach_account_pool import (
    OutreachAccountPool,
    OutreachAccountPoolSettings,
)
from app.outreach_scheduler import (
    OutreachScheduler,
)
from app.outreach_scheduler_state import (
    OutreachSchedulerState,
)


@dataclass
class FakeStateStore:
    state: OutreachSchedulerState

    def load(
        self,
    ) -> OutreachSchedulerState:
        return self.state

    def save(
        self,
        *,
        current_account_id: str,
        used_in_current_turn: int,
        turn_limit: int,
    ) -> OutreachSchedulerState:
        self.state = OutreachSchedulerState(
            scheduler_name=(
                self.state.scheduler_name
            ),
            current_account_id=(
                current_account_id
            ),
            used_in_current_turn=(
                used_in_current_turn
            ),
            turn_limit=turn_limit,
        )

        return self.state

    def increment_usage(
        self,
        *,
        amount: int = 1,
    ) -> OutreachSchedulerState:
        new_used = (
            self.state.used_in_current_turn
            + amount
        )

        if new_used > self.state.turn_limit:
            raise RuntimeError(
                "Turn limit exceeded"
            )

        return self.save(
            current_account_id=(
                self.state.current_account_id
            ),
            used_in_current_turn=new_used,
            turn_limit=(
                self.state.turn_limit
            ),
        )

    def move_to_account(
        self,
        *,
        account_id: str,
        turn_limit: int,
    ) -> OutreachSchedulerState:
        return self.save(
            current_account_id=account_id,
            used_in_current_turn=0,
            turn_limit=turn_limit,
        )


def build_scheduler(
) -> OutreachScheduler:
    account_pool = OutreachAccountPool(
        settings=(
            OutreachAccountPoolSettings(
                profile_root=__import__(
                    "pathlib"
                ).Path(
                    "outreach_browser_profiles"
                ),
                account_ids=(
                    "outreach_account_01",
                    "outreach_account_02",
                    "outreach_account_03",
                    "outreach_account_04",
                    "outreach_account_05",
                ),
                profiles_per_account_turn=10,
            )
        )
    )

    fake_state_store = FakeStateStore(
        state=OutreachSchedulerState(
            scheduler_name=(
                "linkedin_outreach"
            ),
            current_account_id=(
                "outreach_account_04"
            ),
            used_in_current_turn=7,
            turn_limit=10,
        )
    )

    scheduler = OutreachScheduler(
        settings=None,  # type: ignore[arg-type]
        account_pool=account_pool,
        state_store=fake_state_store,  # type: ignore[arg-type]
    )

    return scheduler


def test_carry_over_from_7_of_10(
) -> None:
    scheduler = build_scheduler()

    turn = scheduler.get_current_turn()

    assert (
        turn.account.account_id
        == "outreach_account_04"
    )

    assert (
        turn.used_in_current_turn
        == 7
    )

    assert (
        turn.remaining_in_current_turn
        == 3
    )

    capacity = scheduler.get_batch_capacity(
        requested_count=8
    )

    assert capacity == 3

    scheduler.record_profile_processed()
    scheduler.record_profile_processed()
    scheduler.record_profile_processed()

    state = scheduler.load_state()

    assert (
        state.current_account_id
        == "outreach_account_04"
    )

    assert (
        state.used_in_current_turn
        == 10
    )

    next_turn = scheduler.get_current_turn()

    assert (
        next_turn.account.account_id
        == "outreach_account_05"
    )

    assert (
        next_turn.used_in_current_turn
        == 0
    )

    assert (
        next_turn.remaining_in_current_turn
        == 10
    )


def test_round_robin_wraps_to_account_01(
) -> None:
    scheduler = build_scheduler()

    scheduler.state_store.state = (
        OutreachSchedulerState(
            scheduler_name=(
                "linkedin_outreach"
            ),
            current_account_id=(
                "outreach_account_05"
            ),
            used_in_current_turn=10,
            turn_limit=10,
        )
    )

    turn = scheduler.get_current_turn()

    assert (
        turn.account.account_id
        == "outreach_account_01"
    )

    assert (
        turn.used_in_current_turn
        == 0
    )

    assert (
        turn.remaining_in_current_turn
        == 10
    )
