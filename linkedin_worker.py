from __future__ import annotations

import os
import random
import signal
import sys
import time
import threading
from app.orchestration.worker_registry import (
    WorkerRegistration,
    WorkerRegistry,
)
from datetime import datetime, timezone
from typing import Any

from app.lark_client import LarkClient
from app.linkedin_account_pool import (
    LinkedInAccount,
    LinkedInAccountPool,
)
from app.linkedin_browser import (
    LinkedInBrowserManager,
    LinkedInSessionError,
)
from app.linkedin_scanner import create_supabase_client
from app.profile_raw_scraper import scrape_profile_raw
from app.profile_snapshot_store import save_profile_snapshot
from app.scan_event_store import LinkedInScanEventStore
from app.settings import Settings, load_settings
from app.source_queue import (
    LinkedInSourceQueue,
    QueueSource,
)
from app.worker_health import LinkedInWorkerHealth
from app.worker_command_store import WorkerCommandStore
from scan_unscanned_profiles import (
    get_result_post_count,
    save_local_output,
)


SOURCE_TABLE = "linkedin_sources"

SCHEDULER_STATE_TABLE = (
    "linkedin_scheduler_state"
)

SCHEDULER_NAME = (
    "main_linkedin_scanner"
)

DEFAULT_IDLE_POLL_SECONDS = 30
DEFAULT_ERROR_RETRY_SECONDS = 60
DEFAULT_STALE_JOB_MINUTES = 20
DEFAULT_ACCOUNT_COOLDOWN_SECONDS = 60
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 30

WORKER_VERSION = "2.4.0-worker-controls"


def _read_int_env(
    key: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw_value = os.getenv(key)

    if raw_value is None:
        value = default
    else:
        try:
            value = int(raw_value.strip())
        except ValueError as exc:
            raise ValueError(
                f"{key} must be an integer"
            ) from exc

    if value < minimum:
        raise ValueError(
            f"{key} must be >= {minimum}"
        )

    if value > maximum:
        raise ValueError(
            f"{key} must be <= {maximum}"
        )

    return value


def _clean_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


class RoundRobinLinkedInWorker:
    """
    Một worker dùng một database Supabase chung.

    Mỗi vòng:
    account_01 -> tối đa 10 URL
    account_02 -> tối đa 10 URL
    ...
    account_05 -> tối đa 10 URL

    Sau account cuối, worker quay lại account đầu tiên.
    """

    def __init__(
        self,
        *,
        settings: Settings,
    ) -> None:
        self.settings = settings

        self.shared_registry = WorkerRegistry(
            settings=settings
        )

        self.shared_registration = WorkerRegistration(
            worker_id=(
                os.getenv(
                    "LINKEDIN_WORKER_ID",
                    "mac_worker_01",
                ).strip()
                or "mac_worker_01"
            ),
            worker_name=(
                os.getenv(
                    "LINKEDIN_WORKER_NAME",
                    "LinkedIn Mac Worker",
                ).strip()
                or "LinkedIn Mac Worker"
            ),
            worker_type="linkedin",
            capabilities=(
                "linkedin_profile_scan",
            ),
            max_concurrent_jobs=1,
            metadata={
                "scanner": "linkedin",
                "account_mode": "round_robin",
            },
        )

        self.account_pool = LinkedInAccountPool()
        self.queue = LinkedInSourceQueue(
            settings=settings
        )

        self.urls_per_account_turn = (
            self.account_pool
            .settings
            .urls_per_account_turn
        )

        self.idle_poll_seconds = _read_int_env(
            "LINKEDIN_WORKER_IDLE_POLL_SECONDS",
            default=DEFAULT_IDLE_POLL_SECONDS,
            minimum=5,
            maximum=3600,
        )

        self.error_retry_seconds = _read_int_env(
            "LINKEDIN_WORKER_ERROR_RETRY_SECONDS",
            default=DEFAULT_ERROR_RETRY_SECONDS,
            minimum=5,
            maximum=3600,
        )

        self.stale_job_minutes = _read_int_env(
            "LINKEDIN_STALE_JOB_MINUTES",
            default=DEFAULT_STALE_JOB_MINUTES,
            minimum=1,
            maximum=1440,
        )

        self.account_cooldown_seconds = _read_int_env(
            "LINKEDIN_ACCOUNT_COOLDOWN_SECONDS",
            default=DEFAULT_ACCOUNT_COOLDOWN_SECONDS,
            minimum=0,
            maximum=3600,
        )

        self.minimum_profile_delay_seconds = _read_int_env(
            "LINKEDIN_MIN_DELAY_SECONDS",
            default=8,
            minimum=0,
            maximum=300,
        )

        self.maximum_profile_delay_seconds = _read_int_env(
            "LINKEDIN_MAX_DELAY_SECONDS",
            default=20,
            minimum=0,
            maximum=300,
        )

        if (
            self.maximum_profile_delay_seconds
            < self.minimum_profile_delay_seconds
        ):
            raise ValueError(
                "LINKEDIN_MAX_DELAY_SECONDS must be "
                "greater than or equal to "
                "LINKEDIN_MIN_DELAY_SECONDS"
            )

        self._stop_requested = False
        self._round_number = 0

        self.heartbeat_interval_seconds = _read_int_env(
            "LINKEDIN_HEARTBEAT_INTERVAL_SECONDS",
            default=DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
            minimum=10,
            maximum=300,
        )

        self._health_lock = threading.Lock()
        self._health_status = "starting"
        self._health_account_id: str | None = None
        self._health_source_id: int | None = None
        self._heartbeat_stop_event = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None

        self.health = LinkedInWorkerHealth(
            settings=settings,
            worker_version=WORKER_VERSION,
        )

        self.events = LinkedInScanEventStore(
            settings=settings,
            worker_id=self.health.worker_id,
        )

        self.commands = WorkerCommandStore(
            settings=settings,
            worker_id=self.health.worker_id,
        )

        self._scan_paused = False
        self._kill_current_requested = threading.Event()
        self._active_browser_lock = threading.Lock()
        self._active_browser: LinkedInBrowserManager | None = None
        self._active_account_id: str | None = None
        self._command_stop_event = threading.Event()
        self._command_thread: threading.Thread | None = None

        self._restore_scheduler_position()

        try:
            self.lark_client: LarkClient | None = (
                LarkClient()
            )
        except Exception as exc:
            self.lark_client = None

            print(
                "Lark client unavailable: "
                f"{type(exc).__name__}: {exc}",
                file=sys.stderr,
            )

    def run_forever(self) -> int:
        self._register_signal_handlers()

        self.shared_registry.register(
            worker=self.shared_registration,
            status="starting",
            worker_version=WORKER_VERSION,
        )

        self.health.register_worker(
            status="starting"
        )
        self._set_live_health_state(
            status="starting",
            account_id=None,
            source_id=None,
        )
        self._start_background_heartbeat()
        self._start_command_listener()

        self.events.emit(
            event_type="worker",
            step_name="worker_started",
            status="processing",
            message="LinkedIn worker started.",
            progress_percent=0,
            metadata={
                "worker_version": WORKER_VERSION,
                "account_count": len(
                    self.account_pool.accounts
                ),
            },
        )

        profile_errors = (
            self.account_pool
            .validate_profiles()
        )

        if profile_errors:
            error_text = "; ".join(profile_errors)
            self.health.mark_error(
                error=error_text
            )
            self.events.emit(
                event_type="worker",
                step_name="account_profiles_invalid",
                status="error",
                message=error_text,
                progress_percent=0,
            )

            print(
                "LinkedIn account sessions are not ready:",
                file=sys.stderr,
            )

            for error in profile_errors:
                print(
                    f"- {error}",
                    file=sys.stderr,
                )

            return 1

        print("")
        print(
            "Starting LinkedIn round-robin worker."
        )
        print(
            f"Worker version: {WORKER_VERSION}"
        )
        print(
            f"Accounts: {len(self.account_pool.accounts)}"
        )
        print(
            "URLs per account turn: "
            f"{self.urls_per_account_turn}"
        )
        print(
            "Database: one shared Supabase queue"
        )
        print(
            "Press Ctrl+C to stop."
        )

        try:
            released = (
                self.queue.release_stale_sources(
                    stale_after_minutes=(
                        self.stale_job_minutes
                    )
                )
            )

            if released:
                print(
                    f"Released {released} stale jobs."
                )

            self._set_live_health_state(
                status="idle",
                account_id=None,
                source_id=None,
            )
            self.health.heartbeat(
                status="idle"
            )
            self.shared_registry.heartbeat(
                worker_id=(
                    self.shared_registration.worker_id
                ),
                status="idle",
                current_job_id=None,
                current_load=0,
            )

            while not self._stop_requested:
                try:
                    if self._scan_paused:
                        self._set_live_health_state(
                            status="paused",
                            account_id=None,
                            source_id=None,
                        )
                        self.health.heartbeat(
                            status="paused"
                        )
                        self._sleep_interruptibly(2)
                        continue

                    self._set_live_health_state(
                        status="idle",
                        account_id=None,
                        source_id=None,
                    )
                    self.health.heartbeat(
                        status="idle"
                    )
                    processed = self.run_one_round()

                except Exception as exc:
                    self.health.mark_error(
                        error=exc
                    )

                    print(
                        "Worker round failed: "
                        f"{type(exc).__name__}: {exc}",
                        file=sys.stderr,
                    )

                    self._sleep_interruptibly(
                        self.error_retry_seconds
                    )
                    continue

                if self._stop_requested:
                    break

                if processed == 0:
                    print(
                        "Queue is empty. "
                        f"Checking again in "
                        f"{self.idle_poll_seconds} seconds."
                    )

                    self._sleep_interruptibly(
                        self.idle_poll_seconds
                    )

            return 0

        except KeyboardInterrupt:
            self.request_stop()
            return 0

        finally:
            self._stop_command_listener()
            self._stop_background_heartbeat()

            try:
                self._set_live_health_state(
                    status="stopping",
                    account_id=None,
                    source_id=None,
                )
                self.health.mark_stopping()
                self.shared_registry.heartbeat(
                    worker_id=(
                        self.shared_registration.worker_id
                    ),
                    status="stopping",
                    current_job_id=None,
                    current_load=0,
                )
            except Exception as exc:
                print(
                    "Could not save stopping heartbeat: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )

            self.events.emit(
                event_type="worker",
                step_name="worker_stopped",
                status="warning",
                message="LinkedIn worker stopped.",
                progress_percent=0,
            )

            print("")
            print(
                "LinkedIn round-robin worker stopped."
            )

    def run_one_round(self) -> int:
        """
        Mỗi round chỉ chạy đúng một account.

        - Có source:
          xử lý batch, lưu account vừa dùng và chuyển sang account kế tiếp.

        - Không có source:
          giữ nguyên account hiện tại và trả về 0 để worker đi vào idle polling.

        Cách này tránh việc worker chạy vòng qua cả 5 account
        liên tục khi queue đang trống.
        """
        self._round_number += 1

        account = self.account_pool.get_next_account()

        print("")
        print("=" * 72)
        print(
            f"Round {self._round_number} started"
        )
        print(
            f"Selected account: {account.account_id}"
        )

        claimed_count = self.run_account_turn(
            account=account
        )

        if claimed_count <= 0:
            self.account_pool.set_next_account(
                account.account_id
            )

            print(
                f"{account.account_id}: queue is empty."
            )
            print(
                "Worker will enter idle polling."
            )
            print(
                "Next scheduled account remains: "
                f"{account.account_id}"
            )

            return 0

        self._save_scheduler_position(
            account_id=account.account_id
        )

        print("")
        print(
            f"Round {self._round_number} completed."
        )
        print(
            f"Sources claimed: {claimed_count}"
        )
        print(
            "Next scheduled account: "
            f"{self.account_pool.next_account_id}"
        )

        if (
            self.account_cooldown_seconds > 0
            and not self._stop_requested
        ):
            print(
                f"{account.account_id} completed "
                f"its turn. Cooldown "
                f"{self.account_cooldown_seconds}s."
            )

            self._sleep_interruptibly(
                self.account_cooldown_seconds
            )

        return claimed_count

    def run_account_turn(
        self,
        *,
        account: LinkedInAccount,
    ) -> int:
        print("")
        print("-" * 72)
        print(
            f"Account turn: {account.account_id}"
        )

        self._set_live_health_state(
            status="scanning",
            account_id=account.account_id,
            source_id=None,
        )
        self.health.mark_batch_started(
            account_id=account.account_id
        )
        self.health.mark_account_scanning(
            account_id=account.account_id
        )
        self.events.emit(
            event_type="account",
            step_name="account_turn_started",
            status="processing",
            message=(
                f"{account.account_id} started "
                "a queue turn."
            ),
            progress_percent=0,
            account_id=account.account_id,
        )

        sources = self.queue.claim_sources(
            account_id=account.account_id,
            limit=self.urls_per_account_turn,
        )

        if not sources:
            self.events.emit(
                event_type="account",
                step_name="queue_empty_for_account",
                status="info",
                message=(
                    f"No pending sources for "
                    f"{account.account_id}."
                ),
                progress_percent=0,
                account_id=account.account_id,
            )
            self.health.mark_account_available(
                account_id=account.account_id
            )
            self.health.mark_batch_completed()

            print(
                f"{account.account_id}: "
                "no pending sources."
            )
            return 0

        print(
            f"{account.account_id}: "
            f"claimed {len(sources)} source(s)."
        )

        for claimed_source in sources:
            self.events.emit(
                event_type="queue",
                step_name="source_claimed",
                status="queued",
                message=(
                    f"Source {claimed_source.id} "
                    f"claimed by {account.account_id}."
                ),
                progress_percent=5,
                source_id=claimed_source.id,
                account_id=account.account_id,
                metadata={
                    "linkedin_url": (
                        claimed_source.linkedin_url
                    ),
                    "batch_size": len(sources),
                },
            )

        browser = account.create_browser_manager()
        self._active_account_id = account.account_id

        with self._active_browser_lock:
            self._active_browser = browser

        account_terminal_status = "available"
        account_terminal_error: Exception | None = None

        try:
            self.events.emit(
                event_type="browser",
                step_name="browser_starting",
                status="processing",
                message=(
                    f"Opening persistent browser "
                    f"session for {account.account_id}."
                ),
                progress_percent=8,
                account_id=account.account_id,
            )
            browser.start()
            self.events.emit(
                event_type="browser",
                step_name="browser_started",
                status="success",
                message=(
                    f"Browser session ready for "
                    f"{account.account_id}."
                ),
                progress_percent=10,
                account_id=account.account_id,
            )

            for index, source in enumerate(
                sources,
                start=1,
            ):
                if self._kill_current_requested.is_set():
                    self.queue.release_account_sources(
                        account_id=account.account_id,
                        reason=(
                            "Current scan was killed from "
                            "the operations dashboard."
                        ),
                    )
                    self._kill_current_requested.clear()
                    break

                if self._scan_paused:
                    self.queue.release_account_sources(
                        account_id=account.account_id,
                        reason=(
                            "Scanner paused from the "
                            "operations dashboard."
                        ),
                    )
                    break

                if self._stop_requested:
                    self.queue.release_account_sources(
                        account_id=account.account_id,
                        reason=(
                            "Worker stopped before "
                            "account turn completed."
                        ),
                    )
                    break

                print("")
                print(
                    f"[{index}/{len(sources)}] "
                    f"{account.account_id} "
                    f"scanning source {source.id}"
                )
                print(
                    f"URL: {source.linkedin_url}"
                )

                self._set_live_health_state(
                    status="scanning",
                    account_id=account.account_id,
                    source_id=source.id,
                )
                self.health.heartbeat(
                    status="scanning",
                    current_account_id=(
                        account.account_id
                    ),
                    current_source_id=source.id,
                )
                self.health.mark_account_scanning(
                    account_id=account.account_id,
                    source_id=source.id,
                )

                try:
                    self._process_source(
                        account=account,
                        source=source,
                        browser=browser,
                    )

                except Exception as exc:
                    if self._kill_current_requested.is_set():
                        self.queue.release_account_sources(
                            account_id=account.account_id,
                            reason=(
                                "Current scan was killed from "
                                "the operations dashboard."
                            ),
                        )
                        self._kill_current_requested.clear()
                        account_terminal_status = "available"
                        account_terminal_error = None
                        print(
                            "Current scan killed from dashboard."
                        )
                        break

                    if isinstance(exc, LinkedInSessionError):
                        account_terminal_status = "needs_login"
                        account_terminal_error = exc
                        self.events.emit(
                            event_type="source",
                            step_name="linkedin_session_invalid",
                            status="error",
                            message=(
                                f"{type(exc).__name__}: {exc}"
                            ),
                            progress_percent=10,
                            source_id=source.id,
                            account_id=account.account_id,
                        )
                        self.health.mark_account_needs_login(
                            account_id=account.account_id,
                            error=exc,
                        )
                        self.health.mark_error(
                            error=exc,
                            account_id=account.account_id,
                            source_id=source.id,
                        )

                        print(
                            f"{account.account_id} requires "
                            "login or verification.",
                            file=sys.stderr,
                        )

                        self.queue.fail_source(
                            source_id=source.id,
                            account_id=account.account_id,
                            error=exc,
                            retryable=True,
                        )

                        released_count = (
                            self.queue
                            .release_account_sources(
                                account_id=(
                                    account.account_id
                                ),
                                reason=(
                                    "Account session requires "
                                    "login or verification."
                                ),
                            )
                        )

                        print(
                            f"Released {released_count} "
                            "remaining source(s).",
                            file=sys.stderr,
                        )

                        self._send_failure_message(
                            source=source,
                            error=exc,
                        )
                        break

                    account_terminal_status = "error"
                    account_terminal_error = exc
                    self.events.emit(
                        event_type="source",
                        step_name="source_failed",
                        status="error",
                        message=(
                            f"{type(exc).__name__}: {exc}"
                        ),
                        progress_percent=0,
                        source_id=source.id,
                        account_id=account.account_id,
                    )
                    self.health.mark_account_error(
                        account_id=account.account_id,
                        error=exc,
                        source_id=source.id,
                    )
                    self.health.mark_error(
                        error=exc,
                        account_id=account.account_id,
                        source_id=source.id,
                    )

                    next_status = self.queue.fail_source(
                        source_id=source.id,
                        account_id=account.account_id,
                        error=exc,
                        retryable=True,
                    )

                    print(
                        f"Source {source.id} failed. "
                        f"Next status: {next_status}. "
                        f"Error: {type(exc).__name__}: {exc}",
                        file=sys.stderr,
                    )

                    self._send_failure_message(
                        source=source,
                        error=exc,
                    )

                if index < len(sources):
                    self._wait_between_profiles()

        finally:
            self.events.emit(
                event_type="browser",
                step_name="browser_stopping",
                status="info",
                message=(
                    f"Closing browser session for "
                    f"{account.account_id}."
                ),
                progress_percent=100,
                account_id=account.account_id,
            )
            browser.stop()

            with self._active_browser_lock:
                if self._active_browser is browser:
                    self._active_browser = None

            self._active_account_id = None

            try:
                if account_terminal_status == "available":
                    self.health.mark_account_available(
                        account_id=account.account_id,
                        success=True,
                    )
                    self.events.emit(
                        event_type="account",
                        step_name="account_turn_completed",
                        status="success",
                        message=(
                            f"{account.account_id} "
                            "completed its turn."
                        ),
                        progress_percent=100,
                        account_id=account.account_id,
                    )
                elif account_terminal_status == "needs_login":
                    self.health.mark_account_needs_login(
                        account_id=account.account_id,
                        error=(
                            account_terminal_error
                            or RuntimeError(
                                "LinkedIn login required"
                            )
                        ),
                    )
                else:
                    self.health.mark_account_error(
                        account_id=account.account_id,
                        error=(
                            account_terminal_error
                            or RuntimeError(
                                "Account turn failed"
                            )
                        ),
                    )

                self.health.mark_batch_completed()

            except Exception as exc:
                print(
                    "Could not update account health: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )

        return len(sources)

    def _process_source(
        self,
        *,
        account: LinkedInAccount,
        source: QueueSource,
        browser: LinkedInBrowserManager,
    ) -> None:
        self.events.emit(
            event_type="source",
            step_name="source_processing_started",
            status="processing",
            message="Starting LinkedIn profile scan.",
            progress_percent=12,
            source_id=source.id,
            account_id=account.account_id,
            metadata={
                "linkedin_url": source.linkedin_url,
            },
        )

        self.queue.heartbeat_source(
            source_id=source.id,
            account_id=account.account_id,
        )
        self.events.emit(
            event_type="source",
            step_name="source_heartbeat_updated",
            status="processing",
            message="Processing heartbeat updated.",
            progress_percent=15,
            source_id=source.id,
            account_id=account.account_id,
        )

        self.events.emit(
            event_type="scraper",
            step_name="profile_scrape_started",
            status="processing",
            message=(
                "Opening LinkedIn profile and "
                "extracting raw profile data."
            ),
            progress_percent=20,
            source_id=source.id,
            account_id=account.account_id,
        )

        result = scrape_profile_raw(
            settings=self.settings,
            source_id=source.id,
            browser=browser,
        )

        self.events.emit(
            event_type="scraper",
            step_name="profile_scrape_completed",
            status="success",
            message=(
                "Profile, experience and recent "
                "post extraction completed."
            ),
            progress_percent=70,
            source_id=source.id,
            account_id=account.account_id,
            metadata={
                "post_count": get_result_post_count(
                    result
                ),
            },
        )

        result_source_id = int(
            result["source_id"]
        )

        if result_source_id != source.id:
            raise RuntimeError(
                "Scraper returned a different "
                "source_id."
            )

        scraped_at = _clean_text(
            result.get("scraped_at")
        )

        if not scraped_at:
            raise RuntimeError(
                "Scraper result is missing scraped_at"
            )

        output_path = save_local_output(
            result
        )
        self.events.emit(
            event_type="storage",
            step_name="local_output_saved",
            status="success",
            message=(
                f"Raw output saved to "
                f"{output_path.resolve()}."
            ),
            progress_percent=78,
            source_id=source.id,
            account_id=account.account_id,
        )

        self.events.emit(
            event_type="storage",
            step_name="snapshot_saving",
            status="processing",
            message="Saving profile snapshot to Supabase.",
            progress_percent=82,
            source_id=source.id,
            account_id=account.account_id,
        )

        snapshot_id = save_profile_snapshot(
            settings=self.settings,
            result=result,
        )

        self.events.emit(
            event_type="storage",
            step_name="snapshot_saved",
            status="success",
            message=(
                f"Snapshot {snapshot_id} saved."
            ),
            progress_percent=90,
            source_id=source.id,
            account_id=account.account_id,
            metadata={
                "snapshot_id": snapshot_id,
            },
        )

        self.queue.complete_source(
            source_id=source.id,
            account_id=account.account_id,
            scanned_at=scraped_at,
        )

        self.events.emit(
            event_type="queue",
            step_name="source_completed",
            status="success",
            message="Source marked completed in queue.",
            progress_percent=94,
            source_id=source.id,
            account_id=account.account_id,
        )

        self.health.mark_success(
            account_id=account.account_id,
            source_id=source.id,
        )
        self.health.mark_account_available(
            account_id=account.account_id,
            success=True,
        )

        print(
            f"Completed source {source.id}."
        )
        print(
            f"Account: {account.account_id}"
        )
        print(
            f"Snapshot ID: {snapshot_id}"
        )
        print(
            "Post captions found: "
            f"{get_result_post_count(result)}"
        )
        print(
            f"Output: {output_path.resolve()}"
        )

        self.events.emit(
            event_type="lark",
            step_name="lark_delivery_started",
            status="processing",
            message="Preparing scan result for Lark.",
            progress_percent=96,
            source_id=source.id,
            account_id=account.account_id,
        )

        self._send_success_message(
            account=account,
            source=source,
            result=result,
            snapshot_id=snapshot_id,
        )

    def _send_success_message(
        self,
        *,
        account: LinkedInAccount,
        source: QueueSource,
        result: dict[str, Any],
        snapshot_id: int,
    ) -> None:
        if not source.lark_chat_id:
            return

        if self.lark_client is None:
            self._update_lark_status(
                source_id=source.id,
                sent_at=None,
                error="Lark client is not available.",
            )
            return

        profile = result.get(
            "profile",
            {},
        )

        if not isinstance(profile, dict):
            profile = {}

        captions = result.get(
            "recent_post_captions",
            [],
        )

        if not isinstance(captions, list):
            captions = []

        name = (
            _clean_text(profile.get("name"))
            or source.name
            or "Unknown"
        )

        lines = [
            "LinkedIn scan completed",
            "",
            f"Name: {name}",
            (
                "Headline: "
                f"{_clean_text(profile.get('headline')) or 'Not found'}"
            ),
            (
                "Location: "
                f"{_clean_text(profile.get('location')) or 'Not found'}"
            ),
            f"Recent post captions: {len(captions)}",
            f"Scanner account: {account.account_id}",
            f"Source ID: {source.id}",
            f"Snapshot ID: {snapshot_id}",
            "Status: Saved successfully",
        ]

        if captions:
            lines.extend(
                [
                    "",
                    "Recent captions:",
                ]
            )

            for index, caption in enumerate(
                captions[:5],
                start=1,
            ):
                preview = _clean_text(
                    caption
                ).replace(
                    "\n",
                    " ",
                )

                if len(preview) > 300:
                    preview = (
                        preview[:297] + "..."
                    )

                lines.append(
                    f"{index}. {preview}"
                )

        try:
            message_result = (
                self.lark_client
                .send_text_to_chat(
                    chat_id=source.lark_chat_id,
                    text="\n".join(lines),
                    deduplication_key=(
                        f"linkedin-result:"
                        f"{source.id}:"
                        f"{result.get('scraped_at', '')}"
                    ),
                )
            )

            self._update_lark_status(
                source_id=source.id,
                sent_at=_utc_now_iso(),
                error=None,
            )

            self.events.emit(
                event_type="lark",
                step_name="lark_delivery_completed",
                status="success",
                message="Scan result sent to Lark.",
                progress_percent=100,
                source_id=source.id,
                account_id=account.account_id,
                metadata={
                    "lark_message_id": (
                        message_result.message_id
                    ),
                },
            )

            print(
                "Lark result sent successfully."
            )
            print(
                "Lark message ID: "
                f"{message_result.message_id}"
            )

        except Exception as exc:
            error_text = (
                f"{type(exc).__name__}: {exc}"
            )

            self._update_lark_status(
                source_id=source.id,
                sent_at=None,
                error=error_text,
            )

            self.events.emit(
                event_type="lark",
                step_name="lark_delivery_failed",
                status="warning",
                message=error_text,
                progress_percent=100,
                source_id=source.id,
                account_id=account.account_id,
            )

            print(
                "Profile saved, but Lark delivery "
                f"failed: {error_text}",
                file=sys.stderr,
            )

    def _send_failure_message(
        self,
        *,
        source: QueueSource,
        error: Exception,
    ) -> None:
        if (
            not source.lark_chat_id
            or self.lark_client is None
        ):
            return

        text = "\n".join(
            [
                "LinkedIn scan failed",
                "",
                f"LinkedIn: {source.linkedin_url}",
                f"Source ID: {source.id}",
                (
                    "Error: "
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
            ]
        )

        try:
            self.lark_client.send_text_to_chat(
                chat_id=source.lark_chat_id,
                text=text,
                deduplication_key=(
                    f"linkedin-failure:"
                    f"{source.id}:"
                    f"{source.lark_message_id or ''}"
                ),
            )
        except Exception as exc:
            print(
                "Could not send Lark failure "
                "message: "
                f"{type(exc).__name__}: {exc}",
                file=sys.stderr,
            )

    def _update_lark_status(
        self,
        *,
        source_id: int,
        sent_at: str | None,
        error: str | None,
    ) -> None:
        client = create_supabase_client(
            self.settings
        )

        response = (
            client
            .table(SOURCE_TABLE)
            .update(
                {
                    "lark_result_sent_at": sent_at,
                    "lark_result_error": (
                        error[:2000]
                        if error
                        else None
                    ),
                }
            )
            .eq(
                "id",
                int(source_id),
            )
            .execute()
        )

        if response.data is None:
            print(
                "Could not update Lark delivery "
                f"status for source {source_id}.",
                file=sys.stderr,
            )
    def _restore_scheduler_position(
        self,
    ) -> None:
        """
        Khôi phục account tiếp theo từ Supabase.

        Nếu chưa có state, bắt đầu từ account_01.
        """
        client = create_supabase_client(
            self.settings
        )

        response = (
            client
            .table(SCHEDULER_STATE_TABLE)
            .select(
                "scheduler_name,last_account_id"
            )
            .eq(
                "scheduler_name",
                SCHEDULER_NAME,
            )
            .limit(1)
            .execute()
        )

        rows = list(
            response.data or []
        )

        if not rows:
            (
                client
                .table(SCHEDULER_STATE_TABLE)
                .insert(
                    {
                        "scheduler_name": (
                            SCHEDULER_NAME
                        ),
                        "last_account_id": None,
                        "updated_at": (
                            _utc_now_iso()
                        ),
                    }
                )
                .execute()
            )

            self.account_pool.set_next_after(
                None
            )

            print(
                "Scheduler state created. "
                "Starting from account_01."
            )
            return

        last_account_id = _clean_text(
            rows[0].get(
                "last_account_id"
            )
        )

        self.account_pool.set_next_after(
            last_account_id or None
        )

        print(
            "Scheduler restored. "
            f"Last account: "
            f"{last_account_id or 'none'}. "
            "Next account: "
            f"{self.account_pool.next_account_id}."
        )

    def _save_scheduler_position(
        self,
        *,
        account_id: str,
    ) -> None:
        """
        Lưu account vừa claim được URL.

        Lần chạy tiếp theo sẽ bắt đầu từ account sau nó.
        """
        cleaned_account_id = _clean_text(
            account_id
        )

        if not cleaned_account_id:
            raise ValueError(
                "account_id cannot be empty"
            )

        client = create_supabase_client(
            self.settings
        )

        (
            client
            .table(SCHEDULER_STATE_TABLE)
            .upsert(
                {
                    "scheduler_name": (
                        SCHEDULER_NAME
                    ),
                    "last_account_id": (
                        cleaned_account_id
                    ),
                    "updated_at": (
                        _utc_now_iso()
                    ),
                },
                on_conflict="scheduler_name",
            )
            .execute()
        )

    
    def _start_command_listener(self) -> None:
        if (
            self._command_thread is not None
            and self._command_thread.is_alive()
        ):
            return

        self._command_stop_event.clear()
        self._command_thread = threading.Thread(
            target=self._command_loop,
            name="linkedin-worker-commands",
            daemon=True,
        )
        self._command_thread.start()

        print("Worker command listener started.")

    def _stop_command_listener(self) -> None:
        self._command_stop_event.set()

        thread = self._command_thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=5)

        self._command_thread = None

    def _command_loop(self) -> None:
        while not self._command_stop_event.wait(1):
            try:
                self._process_control_commands()
            except Exception as exc:
                print(
                    "Worker command listener failed: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )

    def _process_control_commands(self) -> None:
        while True:
            command = self.commands.claim_next_command()

            if command is None:
                return

            try:
                if command.command == "stop_scan":
                    self._scan_paused = True
                    self._set_live_health_state(
                        status="paused",
                        account_id=self._active_account_id,
                        source_id=None,
                    )
                    self.health.heartbeat(
                        status="paused",
                        current_account_id=(
                            self._active_account_id
                        ),
                    )

                elif command.command == "resume_scan":
                    self._scan_paused = False
                    self._set_live_health_state(
                        status="idle",
                        account_id=None,
                        source_id=None,
                    )
                    self.health.heartbeat(
                        status="idle"
                    )

                elif command.command == "kill_current":
                    self._kill_current_requested.set()

                    with self._active_browser_lock:
                        browser = self._active_browser

                    if browser is not None:
                        try:
                            browser.stop()
                        except Exception as exc:
                            print(
                                "Could not stop active browser: "
                                f"{type(exc).__name__}: {exc}",
                                file=sys.stderr,
                            )

                else:
                    raise ValueError(
                        "Unsupported worker command: "
                        f"{command.command}"
                    )

                self.commands.complete(
                    command_id=command.id
                )

            except Exception as exc:
                self.commands.fail(
                    command_id=command.id,
                    error=exc,
                )
                raise


    @staticmethod
    def _to_shared_worker_status(
        status: str,
    ) -> str:
        """
        Chuyển trạng thái LinkedIn cũ
        sang trạng thái worker dùng chung.
        """

        cleaned_status = str(
            status or ""
        ).strip().lower()

        status_map = {
            "starting": "starting",
            "idle": "idle",
            "scanning": "busy",
            "paused": "paused",
            "stopping": "stopping",
            "error": "error",
        }

        return status_map.get(
            cleaned_status,
            "error",
        )

    def _set_live_health_state(
        self,
        *,
        status: str,
        account_id: str | None,
        source_id: int | None,
    ) -> None:
        with self._health_lock:
            self._health_status = status
            self._health_account_id = account_id
            self._health_source_id = source_id

    def _start_background_heartbeat(self) -> None:
        if (
            self._heartbeat_thread is not None
            and self._heartbeat_thread.is_alive()
        ):
            return

        self._heartbeat_stop_event.clear()

        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name="linkedin-worker-heartbeat",
            daemon=True,
        )
        self._heartbeat_thread.start()

        print(
            "Background heartbeat: every "
            f"{self.heartbeat_interval_seconds}s"
        )

    def _stop_background_heartbeat(self) -> None:
        self._heartbeat_stop_event.set()

        thread = self._heartbeat_thread

        if (
            thread is not None
            and thread.is_alive()
        ):
            thread.join(timeout=5)

        self._heartbeat_thread = None

    def _heartbeat_loop(self) -> None:
        while not self._heartbeat_stop_event.wait(
            self.heartbeat_interval_seconds
        ):
            with self._health_lock:
                status = self._health_status
                account_id = self._health_account_id
                source_id = self._health_source_id

            try:
                self.health.touch_heartbeat(
                    status=status,
                    current_account_id=account_id,
                    current_source_id=source_id,
                )

                self.shared_registry.heartbeat(
                    worker_id=(
                        self.shared_registration.worker_id
                    ),
                    status=self._to_shared_worker_status(
                        status
                    ),
                    current_job_id=None,
                    current_load=(
                        1
                        if status == "scanning"
                        else 0
                    ),
                )
            except Exception as exc:
                print(
                    "Background heartbeat failed: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )

    def _wait_between_profiles(self) -> None:
        if (
            self.maximum_profile_delay_seconds
            <= 0
        ):
            return

        seconds = random.randint(
            self.minimum_profile_delay_seconds,
            self.maximum_profile_delay_seconds,
        )

        print(
            f"Waiting {seconds} seconds "
            "before next profile..."
        )

        self._sleep_interruptibly(
            seconds
        )

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

    def request_stop(
        self,
        signum: int | None = None,
        frame: Any = None,
    ) -> None:
        del frame

        self._stop_requested = True

        if signum is not None:
            print("")
            print(
                f"Stop signal received: {signum}"
            )

        print(
            "Worker will stop safely."
        )

    def _register_signal_handlers(
        self,
    ) -> None:
        signal.signal(
            signal.SIGINT,
            self.request_stop,
        )

        if hasattr(signal, "SIGTERM"):
            signal.signal(
                signal.SIGTERM,
                self.request_stop,
            )


def main() -> int:
    try:
        settings = load_settings()

        worker = RoundRobinLinkedInWorker(
            settings=settings
        )

        return worker.run_forever()

    except Exception as exc:
        print(
            "Could not start round-robin worker: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
