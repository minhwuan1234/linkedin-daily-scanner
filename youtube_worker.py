from __future__ import annotations

import signal
import sys
import threading
import time
from typing import Any

from app.orchestration.worker_registry import (
    WorkerRegistration,
    WorkerRegistry,
)
from app.settings import Settings, load_settings
from app.youtube_job_queue import YouTubeJobQueue


WORKER_VERSION = "0.1.0"
HEARTBEAT_INTERVAL_SECONDS = 30


class YouTubeWorker:
    """
    YouTube worker tối thiểu.

    Hiện tại worker chỉ:
    - đăng ký vào scanner_workers;
    - gửi heartbeat;
    - giữ trạng thái idle;
    - dừng an toàn.
    """

    def __init__(
        self,
        *,
        settings: Settings,
    ) -> None:
        self.settings = settings

        self.registry = WorkerRegistry(
            settings=settings,
        )

        self.queue = YouTubeJobQueue(
            settings=settings,
        )

        self.registration = WorkerRegistration(
            worker_id="youtube-hermes-01",
            worker_name="YouTube Hermes Worker",
            worker_type="youtube",
            capabilities=(
                "youtube_scan",
            ),
            max_concurrent_jobs=1,
            metadata={
                "scanner": "youtube",
                "engine": "hermes",
            },
        )

        self._stop_requested = False
        self._heartbeat_stop_event = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None

    def run_forever(
        self,
    ) -> int:
        """
        Khởi động worker và giữ worker sống.
        """

        self._register_signal_handlers()

        self.registry.register(
            worker=self.registration,
            status="starting",
            worker_version=WORKER_VERSION,
        )

        self.registry.heartbeat(
            worker_id=self.registration.worker_id,
            status="idle",
            current_job_id=None,
            current_load=0,
        )

        self._start_background_heartbeat()

        print("")
        print("YouTube Hermes Worker started.")
        print(f"Worker ID: {self.registration.worker_id}")
        print(f"Worker version: {WORKER_VERSION}")
        print("Status: idle")
        print("Press Ctrl+C to stop.")

        try:
            while not self._stop_requested:
                job = self.queue.claim_next_job(
                    worker_id=self.registration.worker_id,
                )

                if job is None:
                    time.sleep(5)
                    continue

                self.registry.heartbeat(
                    worker_id=self.registration.worker_id,
                    status="busy",
                    current_job_id=job.id,
                    current_load=1,
                )

                print("")
                print("YouTube job claimed.")
                print(f"Job ID: {job.id}")
                print(f"Keyword: {job.keyword}")
                print(f"Max results: {job.max_results}")

                try:
                    self.queue.heartbeat_job(
                        job_id=job.id,
                        worker_id=self.registration.worker_id,
                        current_stage="ready_for_hermes",
                        progress_percent=10,
                    )

                    time.sleep(3)

                    self.queue.release_job(
                        job_id=job.id,
                        worker_id=self.registration.worker_id,
                        reason=(
                            "Released after worker integration test"
                        ),
                    )

                finally:
                    self.registry.heartbeat(
                        worker_id=self.registration.worker_id,
                        status="idle",
                        current_job_id=None,
                        current_load=0,
                    )

            return 0

        except KeyboardInterrupt:
            self.request_stop()
            return 0

        finally:
            self._stop_background_heartbeat()

            try:
                self.registry.heartbeat(
                    worker_id=self.registration.worker_id,
                    status="stopping",
                    current_job_id=None,
                    current_load=0,
                )
            except Exception as exc:
                print(
                    "Could not save stopping state: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )

            print("")
            print("YouTube Hermes Worker stopped.")

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
                self.registry.heartbeat(
                    worker_id=self.registration.worker_id,
                    status="idle",
                    current_job_id=None,
                    current_load=0,
                )

            except Exception as exc:
                print(
                    "YouTube heartbeat failed: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )

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
            settings=settings,
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
