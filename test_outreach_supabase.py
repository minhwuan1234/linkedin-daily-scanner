from app.settings import load_settings
from app.outreach_scheduler_state import (
    OutreachSchedulerStateStore,
)


def print_state(label: str, state) -> None:
    print("")
    print(label)
    print("------------------------------")
    print(
        f"current_account_id: "
        f"{state.current_account_id}"
    )
    print(
        f"used_in_current_turn: "
        f"{state.used_in_current_turn}"
    )
    print(
        f"turn_limit: "
        f"{state.turn_limit}"
    )
    print(
        f"remaining: "
        f"{state.remaining_in_current_turn}"
    )


def main() -> None:
    settings = load_settings()

    store = OutreachSchedulerStateStore(
        settings=settings
    )

    original_state = store.load()

    print_state(
        "ORIGINAL STATE",
        original_state,
    )

    test_state = store.save(
        current_account_id=(
            "outreach_account_04"
        ),
        used_in_current_turn=7,
        turn_limit=10,
    )

    print_state(
        "TEST STATE WRITTEN",
        test_state,
    )

    loaded_test_state = store.load()

    print_state(
        "TEST STATE READ BACK",
        loaded_test_state,
    )

    restored_state = store.save(
        current_account_id=(
            original_state.current_account_id
        ),
        used_in_current_turn=(
            original_state.used_in_current_turn
        ),
        turn_limit=(
            original_state.turn_limit
        ),
    )

    print_state(
        "RESTORED STATE",
        restored_state,
    )


if __name__ == "__main__":
    main()
