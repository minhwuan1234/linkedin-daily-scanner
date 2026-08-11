from app.settings import load_settings
from app.outreach_scheduler_state import (
    OutreachSchedulerStateStore,
)


def main() -> None:
    settings = load_settings()

    store = OutreachSchedulerStateStore(
        settings=settings
    )

    state = store.load()

    print("")
    print("OUTREACH SUPABASE CONNECTION OK")
    print("------------------------------")
    print(
        f"scheduler_name: "
        f"{state.scheduler_name}"
    )
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


if __name__ == "__main__":
    main()
