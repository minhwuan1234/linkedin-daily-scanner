from __future__ import annotations

import signal
import sys
import time
from dataclasses import dataclass
from typing import Any

from supabase import Client, create_client

from app.linkedin_connect_action import (
    LinkedInConnectResult,
    connect_profile,
)
from app.outreach_account_usage import (
    OutreachAccountUsageStore,
)
from app.outreach_job_queue import (
    OutreachConnectJob,
    OutreachJobQueue,
)
from app.outreach_result_store import (
    save_connect_result,
)
from app.outreach_scheduler import (
    OutreachAccountTurn,
    OutreachScheduler,
)
from app.settings import (
    Settings,
    load_settings,
)


TARGET_TABLE = "outreach_job_targets"

IDLE_POLL_SECONDS = 10

PROFILE_DELAY_SECONDS = 2.5

ACCOUNT_SWITCH_DELAY_SECONDS = 5

NO_ACCOUNT_QUOTA_RECHECK_SECONDS = 60


# =========================================================
# DATA
# =========================================================


@dataclass(frozen=True)
class OutreachTarget:
    target_id: str
    job_id: str
    prospect_id: str
    linkedin_url: str


@dataclass(frozen=True)
class AccountTurnResult:
    processed: int
    quota_exhausted: bool


# =========================================================
# SUPABASE
# =========================================================


def get_client(
    *,
    settings: Settings,
) -> Client:
    return create_client(
        settings.outreach_supabase_url,
        settings.outreach_supabase_secret_key,
    )


# =========================================================
# LOAD TARGETS
# =========================================================


def load_pending_targets(
    *,
    client: Client,
    job_id: str,
) -> list[OutreachTarget]:
    """
    Chỉ lấy target thuộc đúng job đang chạy
    và chưa được worker xử lý.
    """

    response = (
        client.table(
            TARGET_TABLE
        )
        .select(
            (
                "id,"
                "job_id,"
                "prospect_id,"
                "status,"
                "outreach_prospects("
                "linkedin_url"
                ")"
            )
        )
        .eq(
            "job_id",
            job_id,
        )
        .eq(
            "status",
            "pending",
        )
        .execute()
    )

    rows = (
        response.data
        if isinstance(
            response.data,
            list,
        )
        else []
    )

    targets: list[
        OutreachTarget
    ] = []

    for row in rows:
        prospect = (
            row.get(
                "outreach_prospects"
            )
            or {}
        )

        linkedin_url = str(
            prospect.get(
                "linkedin_url",
                "",
            )
            or ""
        ).strip()

        if not linkedin_url:
            continue

        targets.append(
            OutreachTarget(
                target_id=str(
                    row["id"]
                ),
                job_id=str(
                    row["job_id"]
                ),
                prospect_id=str(
                    row["prospect_id"]
                ),
                linkedin_url=linkedin_url,
            )
        )

    return targets


# =========================================================
# PROCESS ONE ACCOUNT TURN
# =========================================================


def process_account_turn(
    *,
    client: Client,
    scheduler: OutreachScheduler,
    usage_store: OutreachAccountUsageStore,
    turn: OutreachAccountTurn,
    targets: list[OutreachTarget],
) -> AccountTurnResult:
    """
    Xử lý tối đa quota của round-robin turn hiện tại.

    Weekly quota là quota riêng:
    - daily: 50 invitation_sent
    - weekly: 250 invitation_sent
    - chỉ invitation_sent mới cộng usage

    Turn quota hiện tại vẫn hoạt động như cũ:
    mỗi target được xử lý vẫn tính 1 turn attempt.
    """

    if not targets:
        return AccountTurnResult(
            processed=0,
            quota_exhausted=False,
        )

    account = turn.account

    usage = usage_store.get_usage(
        account_id=account.account_id
    )

    if not usage.is_available:
        print(
            "Account quota exhausted before turn:",
            account.account_id,
        )

        print(
            "Daily:",
            f"{usage.daily_success_count}/{usage.daily_limit}",
        )

        print(
            "Weekly:",
            f"{usage.weekly_success_count}/{usage.weekly_limit}",
        )

        return AccountTurnResult(
            processed=0,
            quota_exhausted=True,
        )

    capacity = min(
        len(targets),
        turn.remaining_in_current_turn,
    )

    if capacity <= 0:
        return AccountTurnResult(
            processed=0,
            quota_exhausted=False,
        )

    batch = targets[
        :capacity
    ]

    print("")
    print("=" * 60)
    print("ACCOUNT TURN")
    print("=" * 60)

    print(
        "Account:",
        getattr(
            account,
            "display_name",
            account.account_id,
        ),
        f"({account.account_id})",
    )

    print(
        "Used before:",
        f"{turn.used_in_current_turn}"
        "/"
        f"{turn.turn_limit}",
    )

    print(
        "Weekly sent:",
        f"{usage.weekly_success_count}"
        "/"
        f"{usage.weekly_limit}",
    )

    print(
        "Batch size:",
        len(batch),
    )

    browser = (
        account
        .create_browser_manager()
    )

    processed = 0
    quota_exhausted = False

    try:
        browser.start()

        for index, target in enumerate(
            batch,
            start=1,
        ):
            # ---------------------------------------------
            # CHECK DAILY / WEEKLY QUOTA BEFORE NEXT URL
            # ---------------------------------------------

            usage = usage_store.get_usage(
                account_id=account.account_id
            )

            if not usage.is_available:
                quota_exhausted = True

                print("")
                print(
                    "Account reached weekly quota."
                )

                print(
                    "Weekly:",
                    f"{usage.weekly_success_count}"
                    "/"
                    f"{usage.weekly_limit}",
                )

                break

            print("")
            print("-" * 60)

            print(
                f"[{index}/{len(batch)}]"
            )

            print(
                "URL:",
                target.linkedin_url,
            )

            # ---------------------------------------------
            # CONNECT
            # ---------------------------------------------

            try:
                result = connect_profile(
                    browser=browser,
                    linkedin_url=(
                        target.linkedin_url
                    ),
                )

            except Exception as exc:
                result = LinkedInConnectResult(
                    linkedin_url=(
                        target.linkedin_url
                    ),
                    final_url="",
                    status="failed",
                    message=(
                        "worker_error: "
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    ),
                )

            # ---------------------------------------------
            # SAVE RESULT
            # ---------------------------------------------

            success = (
                save_connect_result(
                    job_id=target.job_id,
                    target_id=target.target_id,
                    prospect_id=(
                        target.prospect_id
                    ),
                    account_id=(
                        account.account_id
                    ),
                    result=result,
                    client=client,
                )
            )

            # ---------------------------------------------
            # DAILY / WEEKLY SUCCESS USAGE
            # ---------------------------------------------
            #
            # CHỈ invitation_sent mới tính.
            #
            # Không tính:
            # - failed
            # - pending
            # - already_connected
            # - connect_unavailable
            # - timeout
            #

            if result.status == "invitation_sent":
                usage = (
                    usage_store
                    .record_invitation_sent(
                        account_id=(
                            account.account_id
                        )
                    )
                )

                print(
                    "Connect quota:",
                    (
                        f"weekly "
                        f"{usage.weekly_success_count}"
                        f"/{usage.weekly_limit}"
                    ),
                )

                if not usage.is_available:
                    quota_exhausted = True

            # ---------------------------------------------
            # ROUND-ROBIN TURN QUOTA
            # ---------------------------------------------
            #
            # Giữ nguyên logic cũ:
            # mọi target đã xử lý đều tính 1 turn attempt.
            #

            scheduler.record_profile_processed(
                amount=1
            )

            processed += 1

            print(
                "RESULT:",
                (
                    "SUCCESS"
                    if success
                    else "FAILED"
                ),
            )

            print(
                "Action status:",
                result.status,
            )

            print(
                "Message:",
                result.message,
            )

            # Nếu vừa chạm weekly limit,
            # dừng account ngay sau target vừa thành công.
            if quota_exhausted:
                print(
                    "Account quota reached; "
                    "switching account after this URL."
                )
                break

            # ---------------------------------------------
            # DELAY BETWEEN PROFILES
            # ---------------------------------------------

            if index < len(batch):
                print(
                    f"Waiting {PROFILE_DELAY_SECONDS}s before next URL..."
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

    return AccountTurnResult(
        processed=processed,
        quota_exhausted=quota_exhausted,
    )


# =========================================================
# CONNECT WORKER
# =========================================================


class OutreachConnectWorker:
    """
    Worker LinkedIn Outreach Connect chạy thường trực.

    Weekly success quota:
    - 100 invitation_sent / account / week

    Nếu account hết quota:
    - skip account
    - chuyển account kế tiếp
    - delay 5 giây trước account mới

    Nếu tất cả account đều hết quota:
    - không fail job
    - giữ job đang chạy
    - recheck quota định kỳ
    """

    def __init__(
        self,
        *,
        settings: Settings,
    ) -> None:
        self.settings = settings

        self.client = get_client(
            settings=settings
        )

        self.queue = OutreachJobQueue(
            settings=settings
        )

        self.scheduler = OutreachScheduler(
            settings=settings
        )

        self.usage_store = (
            OutreachAccountUsageStore(
                settings=settings,
                client=self.client,
            )
        )

        self._stop_requested = False

    # =====================================================
    # RUN FOREVER
    # =====================================================

    def run_forever(
        self,
    ) -> int:
        self._register_signal_handlers()

        print("")
        print("=" * 60)
        print("OUTREACH CONNECT WORKER")
        print("=" * 60)

        print(
            "Status: idle"
        )

        print(
            "Poll interval:",
            f"{IDLE_POLL_SECONDS}s",
        )

        print(
            "Weekly Connect success limit:",
            "100/account",
        )

        print(
            "Account switch delay:",
            f"{ACCOUNT_SWITCH_DELAY_SECONDS}s",
        )

        print(
            "Press Ctrl+C to stop."
        )

        try:
            while not self._stop_requested:
                job = (
                    self._claim_next_job_safely()
                )

                if job is None:
                    self._sleep_interruptibly(
                        IDLE_POLL_SECONDS
                    )
                    continue

                self._process_job(
                    job
                )

            return 0

        except KeyboardInterrupt:
            self.request_stop()
            return 0

        finally:
            print("")
            print(
                "Outreach Connect Worker stopped."
            )

    # =====================================================
    # CLAIM
    # =====================================================

    def _claim_next_job_safely(
        self,
    ) -> OutreachConnectJob | None:
        try:
            return (
                self.queue
                .claim_next_job()
            )

        except Exception as exc:
            print(
                (
                    "Could not claim Outreach job: "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
                file=sys.stderr,
            )

            return None

    # =====================================================
    # ACCOUNT QUOTA SELECTION
    # =====================================================

    def _get_available_turn(
        self,
    ) -> OutreachAccountTurn | None:
        """
        Tìm account tiếp theo còn weekly quota.

        Tối đa scan đúng số account trong pool.
        Nếu cả pool đều hết quota -> None.
        """

        account_count = len(
            self.scheduler
            .account_pool
            .accounts
        )

        for _ in range(account_count):
            turn = (
                self.scheduler
                .get_current_turn()
            )

            account = turn.account

            usage = (
                self.usage_store
                .get_usage(
                    account_id=(
                        account.account_id
                    )
                )
            )

            if usage.is_available:
                return turn

            print("")
            print(
                "Skipping account with no quota:",
                getattr(
                    account,
                    "display_name",
                    account.account_id,
                ),
                f"({account.account_id})",
            )

            print(
                "Weekly:",
                (
                    f"{usage.weekly_success_count}"
                    f"/{usage.weekly_limit}"
                ),
            )

            self.scheduler.move_to_next_account(
                state=(
                    self.scheduler
                    .load_state()
                )
            )

        return None

    # =====================================================
    # PROCESS ONE JOB
    # =====================================================

    def _process_job(
        self,
        job: OutreachConnectJob,
    ) -> None:
        print("")
        print("=" * 60)
        print("OUTREACH CONNECT JOB CLAIMED")
        print("=" * 60)

        print(
            "job_code:",
            job.job_code,
        )

        print(
            "job_id:",
            job.id,
        )

        print(
            "input_count:",
            job.input_count,
        )

        print(
            "target_count:",
            job.target_count,
        )

        print(
            "duplicate_count:",
            job.duplicate_count,
        )

        try:
            targets = load_pending_targets(
                client=self.client,
                job_id=job.id,
            )

            print(
                "pending targets:",
                len(targets),
            )

            if not targets:
                print(
                    "Nothing to process."
                )

                self.queue.complete_job(
                    job_id=job.id,
                )

                print(
                    "Job completed."
                )

                return

            offset = 0

            previous_account_id: str | None = None

            while (
                offset < len(targets)
                and not self._stop_requested
            ):
                # -----------------------------------------
                # FIND ACCOUNT WITH QUOTA
                # -----------------------------------------

                turn = self._get_available_turn()

                if turn is None:
                    print("")
                    print(
                        "All Outreach accounts are at "
                        "weekly Connect limit."
                    )

                    print(
                        "Job remains running."
                    )

                    print(
                        (
                            "Rechecking quota in "
                            f"{NO_ACCOUNT_QUOTA_RECHECK_SECONDS}s..."
                        )
                    )

                    self._sleep_interruptibly(
                        NO_ACCOUNT_QUOTA_RECHECK_SECONDS
                    )

                    continue

                current_account_id = (
                    turn.account.account_id
                )

                # -----------------------------------------
                # DELAY WHEN ACCOUNT CHANGES
                # -----------------------------------------

                if (
                    previous_account_id is not None
                    and current_account_id
                    != previous_account_id
                ):
                    print("")
                    print(
                        "Account switched:",
                        previous_account_id,
                        "->",
                        current_account_id,
                    )

                    print(
                        (
                            f"Waiting "
                            f"{ACCOUNT_SWITCH_DELAY_SECONDS}s "
                            "before starting next account..."
                        )
                    )

                    self._sleep_interruptibly(
                        ACCOUNT_SWITCH_DELAY_SECONDS
                    )

                    if self._stop_requested:
                        break

                remaining_targets = (
                    targets[offset:]
                )

                turn_result = (
                    process_account_turn(
                        client=self.client,
                        scheduler=self.scheduler,
                        usage_store=(
                            self.usage_store
                        ),
                        turn=turn,
                        targets=(
                            remaining_targets
                        ),
                    )
                )

                # -----------------------------------------
                # ACCOUNT HIT DAILY/WEEKLY LIMIT
                # -----------------------------------------

                if turn_result.quota_exhausted:
                    current_state = (
                        self.scheduler
                        .load_state()
                    )

                    # Nếu round-robin turn chưa tự complete,
                    # chủ động chuyển account ngay.
                    if (
                        current_state.current_account_id
                        == current_account_id
                    ):
                        self.scheduler.move_to_next_account(
                            state=current_state
                        )

                if turn_result.processed <= 0:
                    if turn_result.quota_exhausted:
                        previous_account_id = (
                            current_account_id
                        )
                        continue

                    raise RuntimeError(
                        "Worker made no progress."
                    )

                offset += (
                    turn_result.processed
                )

                previous_account_id = (
                    current_account_id
                )

                print("")
                print(
                    "Job progress:",
                    f"{offset}/{len(targets)}",
                )

            if self._stop_requested:
                raise RuntimeError(
                    "Worker stop requested "
                    "before job completed."
                )

            self.queue.complete_job(
                job_id=job.id,
            )

            print("")
            print("=" * 60)
            print("JOB FINISHED")
            print("=" * 60)

            print(
                "job_code:",
                job.job_code,
            )

            print(
                "Processed this run:",
                offset,
            )

        except Exception as exc:
            error_message = (
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            print(
                (
                    "Outreach job failed: "
                    f"{error_message}"
                ),
                file=sys.stderr,
            )

            try:
                self.queue.fail_job(
                    job_id=job.id,
                    error_message=(
                        error_message
                    ),
                )

            except Exception as queue_exc:
                print(
                    (
                        "Could not mark job failed: "
                        f"{type(queue_exc).__name__}: "
                        f"{queue_exc}"
                    ),
                    file=sys.stderr,
                )

    # =====================================================
    # STOP
    # =====================================================

    def request_stop(
        self,
        signum: int | None = None,
        frame: Any = None,
    ) -> None:
        del frame

        self._stop_requested = True

        print("")

        if signum is not None:
            print(
                "Stop signal received:",
                signum,
            )

        print(
            "Outreach worker will stop safely."
        )

    def _register_signal_handlers(
        self,
    ) -> None:
        signal.signal(
            signal.SIGINT,
            self.request_stop,
        )

        if hasattr(
            signal,
            "SIGTERM",
        ):
            signal.signal(
                signal.SIGTERM,
                self.request_stop,
            )

    # =====================================================
    # IDLE WAIT
    # =====================================================

    def _sleep_interruptibly(
        self,
        seconds: int,
    ) -> None:
        remaining = max(
            0,
            int(seconds),
        )

        while (
            remaining > 0
            and not self._stop_requested
        ):
            time.sleep(1)
            remaining -= 1


# =========================================================
# MAIN
# =========================================================


def main() -> int:
    try:
        settings = load_settings()

        worker = OutreachConnectWorker(
            settings=settings
        )

        return worker.run_forever()

    except Exception as exc:
        print(
            (
                "Could not start Outreach "
                "Connect Worker: "
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
IDLE_POLL_SECONDS = 10

PROFILE_DELAY_SECONDS = 2.5

ACCOUNT_SWITCH_DELAY_SECONDS = 5

NO_ACCOUNT_QUOTA_RECHECK_SECONDS = 60


# =========================================================
# DATA
# =========================================================


@dataclass(frozen=True)
class OutreachTarget:
    target_id: str
    job_id: str
    prospect_id: str
    linkedin_url: str


@dataclass(frozen=True)
class AccountTurnResult:
    processed: int
    quota_exhausted: bool


# =========================================================
# SUPABASE
# =========================================================


def get_client(
    *,
    settings: Settings,
) -> Client:
    return create_client(
        settings.outreach_supabase_url,
        settings.outreach_supabase_secret_key,
    )


# =========================================================
# LOAD TARGETS
# =========================================================


def load_pending_targets(
    *,
    client: Client,
    job_id: str,
) -> list[OutreachTarget]:
    """
    Chỉ lấy target thuộc đúng job đang chạy
    và chưa được worker xử lý.
    """

    response = (
        client.table(
            TARGET_TABLE
        )
        .select(
            (
                "id,"
                "job_id,"
                "prospect_id,"
                "status,"
                "outreach_prospects("
                "linkedin_url"
                ")"
            )
        )
        .eq(
            "job_id",
            job_id,
        )
        .eq(
            "status",
            "pending",
        )
        .execute()
    )

    rows = (
        response.data
        if isinstance(
            response.data,
            list,
        )
        else []
    )

    targets: list[
        OutreachTarget
    ] = []

    for row in rows:
        prospect = (
            row.get(
                "outreach_prospects"
            )
            or {}
        )

        linkedin_url = str(
            prospect.get(
                "linkedin_url",
                "",
            )
            or ""
        ).strip()

        if not linkedin_url:
            continue

        targets.append(
            OutreachTarget(
                target_id=str(
                    row["id"]
                ),
                job_id=str(
                    row["job_id"]
                ),
                prospect_id=str(
                    row["prospect_id"]
                ),
                linkedin_url=linkedin_url,
            )
        )

    return targets


# =========================================================
# PROCESS ONE ACCOUNT TURN
# =========================================================


def process_account_turn(
    *,
    client: Client,
    scheduler: OutreachScheduler,
    usage_store: OutreachAccountUsageStore,
    turn: OutreachAccountTurn,
    targets: list[OutreachTarget],
) -> AccountTurnResult:
    """
    Xử lý tối đa quota của round-robin turn hiện tại.

    Daily / weekly quota là quota riêng:
    - daily: 50 invitation_sent
    - weekly: 250 invitation_sent
    - chỉ invitation_sent mới cộng usage

    Turn quota hiện tại vẫn hoạt động như cũ:
    mỗi target được xử lý vẫn tính 1 turn attempt.
    """

    if not targets:
        return AccountTurnResult(
            processed=0,
            quota_exhausted=False,
        )

    account = turn.account

    usage = usage_store.get_usage(
        account_id=account.account_id
    )

    if not usage.is_available:
        print(
            "Account quota exhausted before turn:",
            account.account_id,
        )

        print(
            "Daily:",
            f"{usage.daily_success_count}/{usage.daily_limit}",
        )

        print(
            "Weekly:",
            f"{usage.weekly_success_count}/{usage.weekly_limit}",
        )

        return AccountTurnResult(
            processed=0,
            quota_exhausted=True,
        )

    capacity = min(
        len(targets),
        turn.remaining_in_current_turn,
    )

    if capacity <= 0:
        return AccountTurnResult(
            processed=0,
            quota_exhausted=False,
        )

    batch = targets[
        :capacity
    ]

    print("")
    print("=" * 60)
    print("ACCOUNT TURN")
    print("=" * 60)

    print(
        "Account:",
        getattr(
            account,
            "display_name",
            account.account_id,
        ),
        f"({account.account_id})",
    )

    print(
        "Used before:",
        f"{turn.used_in_current_turn}"
        "/"
        f"{turn.turn_limit}",
    )

    print(
        "Daily sent:",
        f"{usage.daily_success_count}"
        "/"
        f"{usage.daily_limit}",
    )

    print(
        "Weekly sent:",
        f"{usage.weekly_success_count}"
        "/"
        f"{usage.weekly_limit}",
    )

    print(
        "Batch size:",
        len(batch),
    )

    browser = (
        account
        .create_browser_manager()
    )

    processed = 0
    quota_exhausted = False

    try:
        browser.start()

        for index, target in enumerate(
            batch,
            start=1,
        ):
            # ---------------------------------------------
            # CHECK DAILY / WEEKLY QUOTA BEFORE NEXT URL
            # ---------------------------------------------

            usage = usage_store.get_usage(
                account_id=account.account_id
            )

            if not usage.is_available:
                quota_exhausted = True

                print("")
                print(
                    "Account reached daily/weekly quota."
                )

                print(
                    "Daily:",
                    f"{usage.daily_success_count}"
                    "/"
                    f"{usage.daily_limit}",
                )

                print(
                    "Weekly:",
                    f"{usage.weekly_success_count}"
                    "/"
                    f"{usage.weekly_limit}",
                )

                break

            print("")
            print("-" * 60)

            print(
                f"[{index}/{len(batch)}]"
            )

            print(
                "URL:",
                target.linkedin_url,
            )

            # ---------------------------------------------
            # CONNECT
            # ---------------------------------------------

            try:
                result = connect_profile(
                    browser=browser,
                    linkedin_url=(
                        target.linkedin_url
                    ),
                )

            except Exception as exc:
                result = LinkedInConnectResult(
                    linkedin_url=(
                        target.linkedin_url
                    ),
                    final_url="",
                    status="failed",
                    message=(
                        "worker_error: "
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    ),
                )

            # ---------------------------------------------
            # SAVE RESULT
            # ---------------------------------------------

            success = (
                save_connect_result(
                    job_id=target.job_id,
                    target_id=target.target_id,
                    prospect_id=(
                        target.prospect_id
                    ),
                    account_id=(
                        account.account_id
                    ),
                    result=result,
                    client=client,
                )
            )

            # ---------------------------------------------
            # DAILY / WEEKLY SUCCESS USAGE
            # ---------------------------------------------
            #
            # CHỈ invitation_sent mới tính.
            #
            # Không tính:
            # - failed
            # - pending
            # - already_connected
            # - connect_unavailable
            # - timeout
            #

            if result.status == "invitation_sent":
                usage = (
                    usage_store
                    .record_invitation_sent(
                        account_id=(
                            account.account_id
                        )
                    )
                )

                print(
                    "Connect quota:",
                    (
                        f"daily "
                        f"{usage.daily_success_count}"
                        f"/{usage.daily_limit}"
                    ),
                    "·",
                    (
                        f"weekly "
                        f"{usage.weekly_success_count}"
                        f"/{usage.weekly_limit}"
                    ),
                )

                if not usage.is_available:
                    quota_exhausted = True

            # ---------------------------------------------
            # ROUND-ROBIN TURN QUOTA
            # ---------------------------------------------
            #
            # Giữ nguyên logic cũ:
            # mọi target đã xử lý đều tính 1 turn attempt.
            #

            scheduler.record_profile_processed(
                amount=1
            )

            processed += 1

            print(
                "RESULT:",
                (
                    "SUCCESS"
                    if success
                    else "FAILED"
                ),
            )

            print(
                "Action status:",
                result.status,
            )

            print(
                "Message:",
                result.message,
            )

            # Nếu vừa chạm daily/weekly limit,
            # dừng account ngay sau target vừa thành công.
            if quota_exhausted:
                print(
                    "Account quota reached; "
                    "switching account after this URL."
                )
                break

            # ---------------------------------------------
            # DELAY BETWEEN PROFILES
            # ---------------------------------------------

            if index < len(batch):
                print(
                    f"Waiting {PROFILE_DELAY_SECONDS}s before next URL..."
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

    return AccountTurnResult(
        processed=processed,
        quota_exhausted=quota_exhausted,
    )


# =========================================================
# CONNECT WORKER
# =========================================================


class OutreachConnectWorker:
    """
    Worker LinkedIn Outreach Connect chạy thường trực.

    Daily/weekly success quota:
    - 50 invitation_sent / account / day
    - 250 invitation_sent / account / week

    Nếu account hết quota:
    - skip account
    - chuyển account kế tiếp
    - delay 5 giây trước account mới

    Nếu tất cả account đều hết quota:
    - không fail job
    - giữ job đang chạy
    - recheck quota định kỳ
    """

    def __init__(
        self,
        *,
        settings: Settings,
    ) -> None:
        self.settings = settings

        self.client = get_client(
            settings=settings
        )

        self.queue = OutreachJobQueue(
            settings=settings
        )

        self.scheduler = OutreachScheduler(
            settings=settings
        )

        self.usage_store = (
            OutreachAccountUsageStore(
                settings=settings,
                client=self.client,
            )
        )

        self._stop_requested = False

    # =====================================================
    # RUN FOREVER
    # =====================================================

    def run_forever(
        self,
    ) -> int:
        self._register_signal_handlers()

        print("")
        print("=" * 60)
        print("OUTREACH CONNECT WORKER")
        print("=" * 60)

        print(
            "Status: idle"
        )

        print(
            "Poll interval:",
            f"{IDLE_POLL_SECONDS}s",
        )

        print(
            "Daily Connect success limit:",
            "50/account",
        )

        print(
            "Weekly Connect success limit:",
            "250/account",
        )

        print(
            "Account switch delay:",
            f"{ACCOUNT_SWITCH_DELAY_SECONDS}s",
        )

        print(
            "Press Ctrl+C to stop."
        )

        try:
            while not self._stop_requested:
                job = (
                    self._claim_next_job_safely()
                )

                if job is None:
                    self._sleep_interruptibly(
                        IDLE_POLL_SECONDS
                    )
                    continue

                self._process_job(
                    job
                )

            return 0

        except KeyboardInterrupt:
            self.request_stop()
            return 0

        finally:
            print("")
            print(
                "Outreach Connect Worker stopped."
            )

    # =====================================================
    # CLAIM
    # =====================================================

    def _claim_next_job_safely(
        self,
    ) -> OutreachConnectJob | None:
        try:
            return (
                self.queue
                .claim_next_job()
            )

        except Exception as exc:
            print(
                (
                    "Could not claim Outreach job: "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
                file=sys.stderr,
            )

            return None

    # =====================================================
    # ACCOUNT QUOTA SELECTION
    # =====================================================

    def _get_available_turn(
        self,
    ) -> OutreachAccountTurn | None:
        """
        Tìm account tiếp theo còn daily + weekly quota.

        Tối đa scan đúng số account trong pool.
        Nếu cả pool đều hết quota -> None.
        """

        account_count = len(
            self.scheduler
            .account_pool
            .accounts
        )

        for _ in range(account_count):
            turn = (
                self.scheduler
                .get_current_turn()
            )

            account = turn.account

            usage = (
                self.usage_store
                .get_usage(
                    account_id=(
                        account.account_id
                    )
                )
            )

            if usage.is_available:
                return turn

            print("")
            print(
                "Skipping account with no quota:",
                getattr(
                    account,
                    "display_name",
                    account.account_id,
                ),
                f"({account.account_id})",
            )

            print(
                "Daily:",
                (
                    f"{usage.daily_success_count}"
                    f"/{usage.daily_limit}"
                ),
            )

            print(
                "Weekly:",
                (
                    f"{usage.weekly_success_count}"
                    f"/{usage.weekly_limit}"
                ),
            )

            self.scheduler.move_to_next_account(
                state=(
                    self.scheduler
                    .load_state()
                )
            )

        return None

    # =====================================================
    # PROCESS ONE JOB
    # =====================================================

    def _process_job(
        self,
        job: OutreachConnectJob,
    ) -> None:
        print("")
        print("=" * 60)
        print("OUTREACH CONNECT JOB CLAIMED")
        print("=" * 60)

        print(
            "job_code:",
            job.job_code,
        )

        print(
            "job_id:",
            job.id,
        )

        print(
            "input_count:",
            job.input_count,
        )

        print(
            "target_count:",
            job.target_count,
        )

        print(
            "duplicate_count:",
            job.duplicate_count,
        )

        try:
            targets = load_pending_targets(
                client=self.client,
                job_id=job.id,
            )

            print(
                "pending targets:",
                len(targets),
            )

            if not targets:
                print(
                    "Nothing to process."
                )

                self.queue.complete_job(
                    job_id=job.id,
                )

                print(
                    "Job completed."
                )

                return

            offset = 0

            previous_account_id: str | None = None

            while (
                offset < len(targets)
                and not self._stop_requested
            ):
                # -----------------------------------------
                # FIND ACCOUNT WITH QUOTA
                # -----------------------------------------

                turn = self._get_available_turn()

                if turn is None:
                    print("")
                    print(
                        "All Outreach accounts are at "
                        "daily/weekly Connect limit."
                    )

                    print(
                        "Job remains running."
                    )

                    print(
                        (
                            "Rechecking quota in "
                            f"{NO_ACCOUNT_QUOTA_RECHECK_SECONDS}s..."
                        )
                    )

                    self._sleep_interruptibly(
                        NO_ACCOUNT_QUOTA_RECHECK_SECONDS
                    )

                    continue

                current_account_id = (
                    turn.account.account_id
                )

                # -----------------------------------------
                # DELAY WHEN ACCOUNT CHANGES
                # -----------------------------------------

                if (
                    previous_account_id is not None
                    and current_account_id
                    != previous_account_id
                ):
                    print("")
                    print(
                        "Account switched:",
                        previous_account_id,
                        "->",
                        current_account_id,
                    )

                    print(
                        (
                            f"Waiting "
                            f"{ACCOUNT_SWITCH_DELAY_SECONDS}s "
                            "before starting next account..."
                        )
                    )

                    self._sleep_interruptibly(
                        ACCOUNT_SWITCH_DELAY_SECONDS
                    )

                    if self._stop_requested:
                        break

                remaining_targets = (
                    targets[offset:]
                )

                turn_result = (
                    process_account_turn(
                        client=self.client,
                        scheduler=self.scheduler,
                        usage_store=(
                            self.usage_store
                        ),
                        turn=turn,
                        targets=(
                            remaining_targets
                        ),
                    )
                )

                # -----------------------------------------
                # ACCOUNT HIT DAILY/WEEKLY LIMIT
                # -----------------------------------------

                if turn_result.quota_exhausted:
                    current_state = (
                        self.scheduler
                        .load_state()
                    )

                    # Nếu round-robin turn chưa tự complete,
                    # chủ động chuyển account ngay.
                    if (
                        current_state.current_account_id
                        == current_account_id
                    ):
                        self.scheduler.move_to_next_account(
                            state=current_state
                        )

                if turn_result.processed <= 0:
                    if turn_result.quota_exhausted:
                        previous_account_id = (
                            current_account_id
                        )
                        continue

                    raise RuntimeError(
                        "Worker made no progress."
                    )

                offset += (
                    turn_result.processed
                )

                previous_account_id = (
                    current_account_id
                )

                print("")
                print(
                    "Job progress:",
                    f"{offset}/{len(targets)}",
                )

            if self._stop_requested:
                raise RuntimeError(
                    "Worker stop requested "
                    "before job completed."
                )

            self.queue.complete_job(
                job_id=job.id,
            )

            print("")
            print("=" * 60)
            print("JOB FINISHED")
            print("=" * 60)

            print(
                "job_code:",
                job.job_code,
            )

            print(
                "Processed this run:",
                offset,
            )

        except Exception as exc:
            error_message = (
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            print(
                (
                    "Outreach job failed: "
                    f"{error_message}"
                ),
                file=sys.stderr,
            )

            try:
                self.queue.fail_job(
                    job_id=job.id,
                    error_message=(
                        error_message
                    ),
                )

            except Exception as queue_exc:
                print(
                    (
                        "Could not mark job failed: "
                        f"{type(queue_exc).__name__}: "
                        f"{queue_exc}"
                    ),
                    file=sys.stderr,
                )

    # =====================================================
    # STOP
    # =====================================================

    def request_stop(
        self,
        signum: int | None = None,
        frame: Any = None,
    ) -> None:
        del frame

        self._stop_requested = True

        print("")

        if signum is not None:
            print(
                "Stop signal received:",
                signum,
            )

        print(
            "Outreach worker will stop safely."
        )

    def _register_signal_handlers(
        self,
    ) -> None:
        signal.signal(
            signal.SIGINT,
            self.request_stop,
        )

        if hasattr(
            signal,
            "SIGTERM",
        ):
            signal.signal(
                signal.SIGTERM,
                self.request_stop,
            )

    # =====================================================
    # IDLE WAIT
    # =====================================================

    def _sleep_interruptibly(
        self,
        seconds: int,
    ) -> None:
        remaining = max(
            0,
            int(seconds),
        )

        while (
            remaining > 0
            and not self._stop_requested
        ):
            time.sleep(1)
            remaining -= 1


# =========================================================
# MAIN
# =========================================================


def main() -> int:
    try:
        settings = load_settings()

        worker = OutreachConnectWorker(
            settings=settings
        )

        return worker.run_forever()

    except Exception as exc:
        print(
            (
                "Could not start Outreach "
                "Connect Worker: "
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
