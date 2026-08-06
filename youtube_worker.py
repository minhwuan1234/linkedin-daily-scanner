from __future__ import annotations

import signal
import sys
import threading
import time
from typing import Any

from app.orchestration.job_event_store import (
    JobEventStore,
)
from app.orchestration.worker_registry import (
    WorkerRegistration,
    WorkerRegistry,
)
from app.settings import Settings, load_settings
from app.youtube_browser import (
    YouTubeBrowserManager,
)
from app.youtube_job_queue import (
    YouTubeJobQueue,
    YouTubeScanJob,
)
from app.youtube_result_store import (
    save_channel_results,
)
from app.youtube_scanner import (
    apply_this_year_filter,
    collect_unique_channels_from_results,
    scan_channel_list,
    search_youtube,
)


WORKER_VERSION = "0.2.0"
HEARTBEAT_INTERVAL_SECONDS = 30
IDLE_POLL_SECONDS = 5


class YouTubeWorker:
    """
    Worker YouTube chạy flow thật:

    - claim job pending;
    - mở browser profile riêng;
    - search keyword;
    - áp dụng filter This year;
    - collect channel URL;
    - scan channel;
    - lưu kết quả vào youtube_scan_channels;
    - complete hoặc retry/fail job;
    - gửi heartbeat và event.
    """

    def __init__(
        self,
        *,
        settings: Settings,
    ) -> None:
        self.settings = settings

        self.registry = WorkerRegistry(
            settings=settings
        )

        self.queue = YouTubeJobQueue(
            settings=settings
        )

        self.registration = WorkerRegistration(
            worker_id="youtube-browser-01",
            worker_name="YouTube Browser Worker",
            worker_type="youtube",
            capabilities=(
                "youtube_scan",
            ),
            max_concurrent_jobs=1,
            metadata={
                "scanner": "youtube",
                "engine": "playwright",
                "browser_profile": "youtube_browser_01",
            },
        )

        self.events = JobEventStore(
            settings=settings,
            worker_id=self.registration.worker_id,
            platform="youtube",
        )

        self._stop_requested = False

        self._heartbeat_stop_event = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None

        self._state_lock = threading.Lock()
        self._current_status = "starting"
        self._current_job_id: str | None = None
        self._current_load = 0

    def run_forever(
        self,
    ) -> int:
        self._register_signal_handlers()

        self.registry.register(
            worker=self.registration,
            status="starting",
            worker_version=WORKER_VERSION,
        )

        self._set_worker_state(
            status="idle",
            current_job_id=None,
            current_load=0,
        )

        self._send_registry_heartbeat()
        self._start_background_heartbeat()

        print("")
        print("YouTube Browser Worker started.")
        print(f"Worker ID: {self.registration.worker_id}")
        print(f"Worker version: {WORKER_VERSION}")
        print("Status: idle")
        print("Press Ctrl+C to stop.")

        try:
            while not self._stop_requested:
                job = self._claim_next_job_safely()

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
            self._stop_background_heartbeat()

            self._set_worker_state(
                status="stopping",
                current_job_id=None,
                current_load=0,
            )

            try:
                self._send_registry_heartbeat()
            except Exception as exc:
                print(
                    "Could not save stopping state: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )

            print("")
            print("YouTube Browser Worker stopped.")

    def _claim_next_job_safely(
        self,
    ) -> YouTubeScanJob | None:
        try:
            return self.queue.claim_next_job(
                worker_id=(
                    self.registration.worker_id
                )
            )

        except Exception as exc:
            print(
                "Could not claim YouTube job: "
                f"{type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
            return None

    def _process_job(
        self,
        job: YouTubeScanJob,
    ) -> None:
        self._set_worker_state(
            status="busy",
            current_job_id=job.id,
            current_load=1,
        )

        self._send_registry_heartbeat()

        print("")
        print("YouTube job claimed.")
        print(f"Job ID: {job.id}")
        print(f"Keyword: {job.keyword}")
        print(f"Max results: {job.max_results}")
        print(f"Filters: {job.filters}")

        self.events.emit(
            job_id=job.id,
            event_type="queue",
            step_name="job_claimed",
            status="processing",
            message="YouTube worker claimed the job.",
            progress_percent=5,
            metadata={
                "keyword": job.keyword,
                "max_results": job.max_results,
                "filters": job.filters,
            },
        )

        browser = YouTubeBrowserManager()

        try:
            browser.start()

            self._update_job_progress(
                job_id=job.id,
                stage="searching",
                progress=15,
                message=(
                    "Opening YouTube search results."
                ),
            )

            page = search_youtube(
                browser=browser,
                keyword=job.keyword,
            )

            apply_this_year_filter(
                page
            )

            self._update_job_progress(
                job_id=job.id,
                stage="collecting_channels",
                progress=35,
                message=(
                    "Collecting unique YouTube channels."
                ),
            )

            channels = (
                collect_unique_channels_from_results(
                    page,
                    max_channels=max(
                        1,
                        int(job.max_results),
                    ),
                )
            )

            if self._stop_requested:
                raise RuntimeError(
                    "Worker stop requested before channel scan."
                )

            self._update_job_progress(
                job_id=job.id,
                stage="scanning_channels",
                progress=55,
                message=(
                    f"Scanning {len(channels)} channels."
                ),
            )

            results = scan_channel_list(
                browser=browser,
                channels=channels,
            )

            if self._stop_requested:
                raise RuntimeError(
                    "Worker stop requested before saving results."
                )

            self._update_job_progress(
                job_id=job.id,
                stage="saving_results",
                progress=85,
                message=(
                    f"Saving {len(results)} channel results."
                ),
            )

            saved_rows = save_channel_results(
                job_id=job.id,
                channels=results,
            )

            self.queue.complete_job(
                job_id=job.id,
                worker_id=(
                    self.registration.worker_id
                ),
                result_count=len(
                    saved_rows
                ),
            )

            self.events.emit(
                job_id=job.id,
                event_type="worker",
                step_name="job_completed",
                status="completed",
                message=(
                    f"Saved {len(saved_rows)} YouTube channels."
                ),
                progress_percent=100,
                metadata={
                    "collected_channel_count": len(
                        channels
                    ),
                    "saved_channel_count": len(
                        saved_rows
                    ),
                },
            )

            print("")
            print("YouTube job completed.")
            print(f"Saved channels: {len(saved_rows)}")

        except Exception as exc:
            error_message = (
                f"{type(exc).__name__}: {exc}"
            )

            print(
                "YouTube job failed: "
                f"{error_message}",
                file=sys.stderr,
            )

            try:
                final_status = self.queue.fail_job(
                    job=job,
                    worker_id=(
                        self.registration.worker_id
                    ),
                    error_message=error_message,
                )
            except Exception as queue_exc:
                final_status = "unknown"

                print(
                    "Could not update failed job: "
                    f"{type(queue_exc).__name__}: "
                    f"{queue_exc}",
                    file=sys.stderr,
                )

            self.events.emit(
                job_id=job.id,
                event_type="worker",
                step_name="job_failed",
                status="error",
                message=error_message,
                progress_percent=0,
                metadata={
                    "queue_status": final_status,
                    "retry_count": (
                        job.retry_count + 1
                    ),
                    "max_retries": job.max_retries,
                },
            )

        finally:
            try:
                browser.stop()
            except Exception as browser_exc:
                print(
                    "Could not close YouTube browser: "
                    f"{type(browser_exc).__name__}: "
                    f"{browser_exc}",
                    file=sys.stderr,
                )

            self._set_worker_state(
                status="idle",
                current_job_id=None,
                current_load=0,
            )

            try:
                self._send_registry_heartbeat()
            except Exception as exc:
                print(
                    "Could not return worker to idle: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )

    def _update_job_progress(
        self,
        *,
        job_id: str,
        stage: str,
        progress: int,
        message: str,
    ) -> None:
        self.queue.heartbeat_job(
            job_id=job_id,
            worker_id=(
                self.registration.worker_id
            ),
            current_stage=stage,
            progress_percent=progress,
        )

        self.events.emit(
            job_id=job_id,
            event_type="worker",
            step_name=stage,
            status="processing",
            message=message,
            progress_percent=progress,
        )

    def _set_worker_state(
        self,
        *,
        status: str,
        current_job_id: str | None,
        current_load: int,
    ) -> None:
        with self._state_lock:
            self._current_status = status
            self._current_job_id = current_job_id
            self._current_load = current_load

    def _get_worker_state(
        self,
    ) -> tuple[str, str | None, int]:
        with self._state_lock:
            return (
                self._current_status,
                self._current_job_id,
                self._current_load,
            )

    def _send_registry_heartbeat(
        self,
    ) -> None:
        status, current_job_id, current_load = (
            self._get_worker_state()
        )

        self.registry.heartbeat(
            worker_id=self.registration.worker_id,
            status=status,
            current_job_id=current_job_id,
            current_load=current_load,
        )

    def _start_background_heartbeat(
        self,
    ) -> None:
        if (
            self._heartbeat_thread is not None
            and self._heartbeat_thread.is_alive()
        ):
            return

        self._heartbeat_stop_event.clear()

        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name="youtube-worker-heartbeat",
            daemon=True,
        )

        self._heartbeat_thread.start()

    def _stop_background_heartbeat(
        self,
    ) -> None:
        self._heartbeat_stop_event.set()

        thread = self._heartbeat_thread

        if (
            thread is not None
            and thread.is_alive()
        ):
            thread.join(timeout=5)

        self._heartbeat_thread = None

    def _heartbeat_loop(
        self,
    ) -> None:
        while not self._heartbeat_stop_event.wait(
            HEARTBEAT_INTERVAL_SECONDS
        ):
            try:
                self._send_registry_heartbeat()

            except Exception as exc:
                print(
                    "YouTube heartbeat failed: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
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
            "YouTube worker will stop safely."
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

        worker = YouTubeWorker(
            settings=settings
        )

        return worker.run_forever()

    except Exception as exc:
        print(
            "Could not start YouTube worker: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
