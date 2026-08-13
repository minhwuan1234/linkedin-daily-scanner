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
from app.outreach_job_queue import (
    OutreachConnectJob,
    OutreachJobQueue,
)
from app.outreach_result_store import (
    save_connect_result,
)
from app.outreach_scheduler import (
    OutreachScheduler,
)
from app.settings import (
    Settings,
    load_settings,
)


TARGET_TABLE = "outreach_job_targets"

IDLE_POLL_SECONDS = 10

PROFILE_DELAY_SECONDS = 2.5


# =========================================================
# DATA
# =========================================================


@dataclass(frozen=True)
class OutreachTarget:
    target_id: str
    job_id: str
    prospect_id: str
    linkedin_url: str


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
    targets: list[OutreachTarget],
) -> int:
    """
    Xử lý tối đa quota còn lại
    của account hiện tại.

    Ví dụ:

    account_01 đang 7/10
    còn 3 slots

    Nếu job còn 8 targets:
        account_01 xử lý 3
        sau đó scheduler chuyển account tiếp theo.

    Return:
        số target đã xử lý.
    """

    if not targets:
        return 0

    turn = (
        scheduler
        .get_current_turn()
    )

    account = turn.account

    capacity = min(
        len(targets),
        turn.remaining_in_current_turn,
    )

    if capacity <= 0:
        return 0

    batch = targets[
        :capacity
    ]

    print("")
    print("=" * 60)
    print("ACCOUNT TURN")
    print("=" * 60)

    print(
        "Account:",
        account.account_id,
    )

    print(
        "Used before:",
        f"{turn.used_in_current_turn}"
        "/"
        f"{turn.turn_limit}",
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

    try:
        browser.start()

        for index, target in enumerate(
            batch,
            start=1,
        ):
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
            # QUOTA
            # ---------------------------------------------
            #
            # Dù success hay failed thì account
            # đã dùng 1 attempt cho profile này.
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

            # ---------------------------------------------
            # DELAY BETWEEN PROFILES
            # ---------------------------------------------
            # Giảm tải browser / LinkedIn giữa 2 URL.
            # Không delay sau URL cuối cùng của batch.

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

    return processed


# =========================================================
# CONNECT WORKER
# =========================================================


class OutreachConnectWorker:
    """
    Worker LinkedIn Outreach Connect chạy thường trực.

    Flow:

    idle
    -> check Outreach Supabase
    -> claim Connect job pending
    -> status = running
    -> process targets
    -> status = completed
    -> idle

    Nếu không có job:
        sleep 10 giây
        rồi check lại.
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
            "Press Ctrl+C to stop."
        )

        try:
            while not self._stop_requested:
                # -----------------------------------------
                # CLAIM NEXT JOB
                # -----------------------------------------

                job = (
                    self._claim_next_job_safely()
                )

                if job is None:
                    self._sleep_interruptibly(
                        IDLE_POLL_SECONDS
                    )
                    continue

                # -----------------------------------------
                # PROCESS JOB
                # -----------------------------------------

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
            # ---------------------------------------------
            # LOAD TARGETS
            # ---------------------------------------------

            targets = load_pending_targets(
                client=self.client,
                job_id=job.id,
            )

            print(
                "pending targets:",
                len(targets),
            )

            # ---------------------------------------------
            # EMPTY JOB
            # ---------------------------------------------

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

            # ---------------------------------------------
            # PROCESS TARGETS
            # ---------------------------------------------

            offset = 0

            while (
                offset < len(targets)
                and not self._stop_requested
            ):
                remaining_targets = (
                    targets[offset:]
                )

                processed = (
                    process_account_turn(
                        client=self.client,
                        scheduler=self.scheduler,
                        targets=(
                            remaining_targets
                        ),
                    )
                )

                if processed <= 0:
                    raise RuntimeError(
                        "Worker made no progress."
                    )

                offset += processed

                print("")
                print(
                    "Job progress:",
                    f"{offset}/{len(targets)}",
                )

            # ---------------------------------------------
            # STOP REQUESTED
            # ---------------------------------------------

            if self._stop_requested:
                raise RuntimeError(
                    "Worker stop requested "
                    "before job completed."
                )

            # ---------------------------------------------
            # COMPLETE
            # ---------------------------------------------

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

            # ---------------------------------------------
            # JOB-LEVEL FAILURE
            # ---------------------------------------------
            #
            # Đây chỉ dùng khi cả worker/job bị lỗi.
            #
            # Một profile timeout / 404 / unavailable
            # không vào đây vì process_account_turn()
            # đã convert thành profile FAILED và
            # tiếp tục profile tiếp theo.
            #

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
