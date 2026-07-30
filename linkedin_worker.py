from __future__ import annotations

import os
import random
import signal
import sys
import time
import threading
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
from app.settings import Settings, load_settings
from app.source_queue import (
    LinkedInSourceQueue,
    QueueSource,
)
from app.worker_health import LinkedInWorkerHealth
from scan_unscanned_profiles import (
    get_result_post_count,
    save_local_output,
)


SOURCE_TABLE = "linkedin_sources"

DEFAULT_IDLE_POLL_SECONDS = 30
DEFAULT_ERROR_RETRY_SECONDS = 60
DEFAULT_STALE_JOB_MINUTES = 20
DEFAULT_ACCOUNT_COOLDOWN_SECONDS = 60
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 30

WORKER_VERSION = "2.2.0-background-heartbeat"


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
        self.health.register_worker(
            status="starting"
        )
        self._set_live_health_state(
            status="starting",
            account_id=None,
            source_id=None,
        )
        self._start_background_heartbeat()

        profile_errors = (
            self.account_pool
            .validate_profiles()
        )

        if profile_errors:
            error_text = "; ".join(profile_errors)
            self.health.mark_error(
                error=error_text
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

            while not self._stop_requested:
                try:
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
            self._stop_background_heartbeat()

            try:
                self._set_live_health_state(
                    status="stopping",
                    account_id=None,
                    source_id=None,
                )
                self.health.mark_stopping()
            except Exception as exc:
                print(
                    "Could not save stopping heartbeat: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )

            print("")
            print(
                "LinkedIn round-robin worker stopped."
            )

    def run_one_round(self) -> int:
        self._round_number += 1
        round_claimed_count = 0

        print("")
        print("=" * 72)
        print(
            f"Round {self._round_number} started"
        )

        for account in self.account_pool.accounts:
            if self._stop_requested:
                break

            claimed_count = self.run_account_turn(
                account=account
            )

            round_claimed_count += claimed_count

            if (
                claimed_count > 0
                and self.account_cooldown_seconds > 0
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

        print("")
        print(
            f"Round {self._round_number} completed."
        )
        print(
            "Sources claimed in round: "
            f"{round_claimed_count}"
        )

        return round_claimed_count

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

        sources = self.queue.claim_sources(
            account_id=account.account_id,
            limit=self.urls_per_account_turn,
        )

        if not sources:
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

        browser = account.create_browser_manager()

        try:
            browser.start()

            for index, source in enumerate(
                sources,
                start=1,
            ):
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

                except LinkedInSessionError as exc:
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

                except Exception as exc:
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

                    next_status = (
                        self.queue.fail_source(
                            source_id=source.id,
                            account_id=account.account_id,
                            error=exc,
                            retryable=True,
                        )
                    )

                    print(
                        f"Source {source.id} failed. "
                        f"Next status: {next_status}. "
                        f"Error: {type(exc).__name__}: "
                        f"{exc}",
                        file=sys.stderr,
                    )

                    self._send_failure_message(
                        source=source,
                        error=exc,
                    )

                if index < len(sources):
                    self._wait_between_profiles()

        finally:
            browser.stop()

            try:
                self.health.mark_account_available(
                    account_id=account.account_id,
                    success=True,
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
        self.queue.heartbeat_source(
            source_id=source.id,
            account_id=account.account_id,
        )

        result = scrape_profile_raw(
            settings=self.settings,
            source_id=source.id,
            browser=browser,
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

        snapshot_id = save_profile_snapshot(
            settings=self.settings,
            result=result,
        )

        self.queue.complete_source(
            source_id=source.id,
            account_id=account.account_id,
            scanned_at=scraped_at,
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
