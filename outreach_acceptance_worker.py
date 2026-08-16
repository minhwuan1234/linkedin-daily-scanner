from __future__ import annotations

import sys
import time
from dataclasses import dataclass

from app.linkedin_acceptance_checker import (
    LinkedInAcceptanceResult,
    check_profile_acceptance,
)
from app.outreach_acceptance_store import (
    create_acceptance_check_run,
    get_outreach_supabase_client,
    group_targets_by_account,
    load_acceptance_targets,
    save_acceptance_result,
    update_acceptance_check_run,
)
from app.outreach_account_pool import (
    OutreachAccountPool,
)


PROFILE_DELAY_SECONDS = 2.5
ACCOUNT_SWITCH_DELAY_SECONDS = 5


@dataclass
class AcceptanceRunCounters:
    checked_count: int = 0
    new_accepted_count: int = 0
    still_pending_count: int = 0
    declined_or_unknown_count: int = 0
    failed_count: int = 0


def _record_result(
    *,
    counters: AcceptanceRunCounters,
    result: LinkedInAcceptanceResult,
) -> None:
    counters.checked_count += 1

    if result.status == "accepted":
        counters.new_accepted_count += 1
        return

    if result.status == "pending":
        counters.still_pending_count += 1
        return

    if result.status == "declined_or_unknown":
        counters.declined_or_unknown_count += 1
        return

    counters.failed_count += 1


def run_acceptance_check(
    *,
    source_job_id: str,
) -> int:
    """
    Run one manual Acceptance Check for one Connect Job.

    Flow:
    1. Load targets from that job which still need checking.
    2. Create one acceptance-check run record.
    3. Group targets by assigned_account_id.
    4. Open each LinkedIn browser profile separately.
    5. Read acceptance state only.
    6. Save each target result.
    7. Save live counters to the check-run record.

    This worker does NOT send Connect requests.
    """

    cleaned_job_id = str(
        source_job_id
        or ""
    ).strip()

    if not cleaned_job_id:
        raise ValueError(
            "source_job_id is required."
        )

    client = (
        get_outreach_supabase_client()
    )

    targets = load_acceptance_targets(
        source_job_id=cleaned_job_id,
        client=client,
    )

    print("")
    print("=" * 60)
    print("OUTREACH ACCEPTANCE CHECK")
    print("=" * 60)
    print(
        "Source job:",
        cleaned_job_id,
    )
    print(
        "Targets to check:",
        len(targets),
    )

    check_run = (
        create_acceptance_check_run(
            source_job_id=cleaned_job_id,
            total_to_check=len(targets),
            client=client,
        )
    )

    check_id = str(
        check_run["id"]
    )

    run_number = int(
        check_run.get(
            "run_number",
            1,
        )
        or 1
    )

    print(
        "Check run:",
        f"#{run_number}",
    )
    print(
        "Check ID:",
        check_id,
    )

    counters = (
        AcceptanceRunCounters()
    )

    # Nothing to check is still a valid completed run.
    if not targets:
        update_acceptance_check_run(
            check_id=check_id,
            checked_count=0,
            new_accepted_count=0,
            still_pending_count=0,
            declined_or_unknown_count=0,
            failed_count=0,
            completed=True,
            client=client,
        )

        print("")
        print(
            "Nothing to check."
        )
        return 0

    grouped = (
        group_targets_by_account(
            targets
        )
    )

    pool = OutreachAccountPool()

    previous_account_id: str | None = None

    try:
        for account_id, account_targets in (
            grouped.items()
        ):
            account = pool.get_account(
                account_id
            )

            # ---------------------------------------------
            # DELAY WHEN SWITCHING LINKEDIN ACCOUNT
            # ---------------------------------------------
            if (
                previous_account_id
                is not None
                and previous_account_id
                != account_id
            ):
                print("")
                print(
                    "Switching account:",
                    previous_account_id,
                    "->",
                    account_id,
                )
                print(
                    f"Waiting "
                    f"{ACCOUNT_SWITCH_DELAY_SECONDS}s..."
                )

                time.sleep(
                    ACCOUNT_SWITCH_DELAY_SECONDS
                )

            print("")
            print("=" * 60)
            print("ACCEPTANCE ACCOUNT")
            print("=" * 60)
            print(
                "Account:",
                account.display_name,
                f"({account.account_id})",
            )
            print(
                "Targets:",
                len(account_targets),
            )

            browser = (
                account
                .create_browser_manager()
            )

            try:
                browser.start()

                for index, target in enumerate(
                    account_targets,
                    start=1,
                ):
                    print("")
                    print("-" * 60)
                    print(
                        f"[{index}/{len(account_targets)}]"
                    )
                    print(
                        "URL:",
                        target["linkedin_url"],
                    )
                    print(
                        "Previous acceptance state:",
                        target[
                            "acceptance_status"
                        ],
                    )

                    try:
                        result = (
                            check_profile_acceptance(
                                browser=browser,
                                linkedin_url=(
                                    target[
                                        "linkedin_url"
                                    ]
                                ),
                            )
                        )

                    except Exception as exc:
                        result = (
                            LinkedInAcceptanceResult(
                                linkedin_url=(
                                    target[
                                        "linkedin_url"
                                    ]
                                ),
                                final_url="",
                                status="check_failed",
                                message=(
                                    "worker_error: "
                                    f"{type(exc).__name__}: "
                                    f"{exc}"
                                ),
                            )
                        )

                    # Save target state first.
                    save_acceptance_result(
                        target_id=(
                            target[
                                "target_id"
                            ]
                        ),
                        result=result,
                        client=client,
                    )

                    # Update in-memory run counters.
                    _record_result(
                        counters=counters,
                        result=result,
                    )

                    # Persist live progress after each profile.
                    update_acceptance_check_run(
                        check_id=check_id,
                        checked_count=(
                            counters
                            .checked_count
                        ),
                        new_accepted_count=(
                            counters
                            .new_accepted_count
                        ),
                        still_pending_count=(
                            counters
                            .still_pending_count
                        ),
                        declined_or_unknown_count=(
                            counters
                            .declined_or_unknown_count
                        ),
                        failed_count=(
                            counters
                            .failed_count
                        ),
                        client=client,
                    )

                    print(
                        "Acceptance status:",
                        result.status,
                    )
                    print(
                        "Message:",
                        result.message,
                    )
                    print(
                        "Run progress:",
                        (
                            f"{counters.checked_count}"
                            f"/{len(targets)}"
                        ),
                    )

                    # -------------------------------------
                    # DELAY BETWEEN PROFILES
                    # -------------------------------------
                    if index < len(
                        account_targets
                    ):
                        print(
                            f"Waiting "
                            f"{PROFILE_DELAY_SECONDS}s "
                            "before next profile..."
                        )

                        time.sleep(
                            PROFILE_DELAY_SECONDS
                        )

            finally:
                try:
                    browser.stop()

                except Exception as exc:
                    print(
                        "Could not close browser:",
                        (
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        ),
                        file=sys.stderr,
                    )

            previous_account_id = (
                account_id
            )

        # ---------------------------------------------
        # COMPLETE RUN
        # ---------------------------------------------
        update_acceptance_check_run(
            check_id=check_id,
            checked_count=(
                counters.checked_count
            ),
            new_accepted_count=(
                counters
                .new_accepted_count
            ),
            still_pending_count=(
                counters
                .still_pending_count
            ),
            declined_or_unknown_count=(
                counters
                .declined_or_unknown_count
            ),
            failed_count=(
                counters.failed_count
            ),
            completed=True,
            client=client,
        )

        print("")
        print("=" * 60)
        print("ACCEPTANCE CHECK FINISHED")
        print("=" * 60)
        print(
            "Checked:",
            counters.checked_count,
        )
        print(
            "New accepted:",
            counters.new_accepted_count,
        )
        print(
            "Still pending:",
            counters.still_pending_count,
        )
        print(
            "Declined / unknown:",
            counters.declined_or_unknown_count,
        )
        print(
            "Check failed:",
            counters.failed_count,
        )

        return 0

    except Exception as exc:
        # Keep counters collected so far and mark run failed.
        update_acceptance_check_run(
            check_id=check_id,
            checked_count=(
                counters.checked_count
            ),
            new_accepted_count=(
                counters
                .new_accepted_count
            ),
            still_pending_count=(
                counters
                .still_pending_count
            ),
            declined_or_unknown_count=(
                counters
                .declined_or_unknown_count
            ),
            failed_count=(
                counters.failed_count
            ),
            failed=True,
            client=client,
        )

        print(
            (
                "Acceptance check failed: "
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
            file=sys.stderr,
        )

        return 1


def main() -> int:
    if len(sys.argv) != 2:
        print("")
        print("Usage:")
        print(
            "python3 outreach_acceptance_worker.py "
            "<source_job_id>"
        )
        print("")
        return 1

    return run_acceptance_check(
        source_job_id=sys.argv[1]
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
