from __future__ import annotations

import os
import random
import signal
import sys
import time
from dataclasses import dataclass
from typing import Any

from app.linkedin_browser import (
    LinkedInBrowserManager,
    LinkedInSessionError,
)
from app.profile_raw_scraper import (
    scrape_profile_raw,
)
from app.profile_snapshot_store import (
    mark_source_scanned,
    save_profile_snapshot,
)
from app.settings import (
    Settings,
    load_settings,
)
from scan_unscanned_profiles import (
    MAX_BATCH_SIZE,
    get_batch_size,
    get_result_post_count,
    get_scan_delay_range,
    get_unscanned_sources,
    save_local_output,
)


DEFAULT_IDLE_POLL_SECONDS = 30
DEFAULT_ERROR_RETRY_SECONDS = 60

MAX_IDLE_POLL_SECONDS = 3600
MAX_ERROR_RETRY_SECONDS = 3600


@dataclass(frozen=True)
class WorkerSettings:
    """
    Cấu hình vòng polling của Mac worker.
    """

    batch_size: int
    idle_poll_seconds: int
    error_retry_seconds: int
    minimum_profile_delay_seconds: int
    maximum_profile_delay_seconds: int

    @classmethod
    def from_environment(
        cls,
    ) -> "WorkerSettings":
        (
            minimum_delay,
            maximum_delay,
        ) = get_scan_delay_range()

        return cls(
            batch_size=get_batch_size(),
            idle_poll_seconds=_read_int_env(
                "LINKEDIN_WORKER_IDLE_POLL_SECONDS",
                default=DEFAULT_IDLE_POLL_SECONDS,
                minimum=5,
                maximum=MAX_IDLE_POLL_SECONDS,
            ),
            error_retry_seconds=_read_int_env(
                "LINKEDIN_WORKER_ERROR_RETRY_SECONDS",
                default=DEFAULT_ERROR_RETRY_SECONDS,
                minimum=5,
                maximum=MAX_ERROR_RETRY_SECONDS,
            ),
            minimum_profile_delay_seconds=(
                minimum_delay
            ),
            maximum_profile_delay_seconds=(
                maximum_delay
            ),
        )


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
            value = int(
                raw_value.strip()
            )
        except ValueError as exc:
            raise ValueError(
                f"Invalid integer environment variable "
                f"{key}={raw_value!r}"
            ) from exc

    if value < minimum:
        raise ValueError(
            f"{key} must be >= {minimum}. "
            f"Received {value}."
        )

    if value > maximum:
        raise ValueError(
            f"{key} must be <= {maximum}. "
            f"Received {value}."
        )

    return value


class LinkedInWorker:
    """
    Worker chạy liên tục trên Mac.

    Một browser persistent được dùng chung cho:
    - nhiều source trong cùng batch
    - nhiều batch liên tiếp

    Browser chỉ đóng khi:
    - worker nhận Ctrl+C
    - process nhận SIGTERM
    - LinkedIn session cần login/checkpoint
    - lỗi browser không thể tiếp tục
    """

    def __init__(
        self,
        *,
        settings: Settings,
        worker_settings: WorkerSettings,
    ) -> None:
        self.settings = settings
        self.worker_settings = worker_settings

        self.browser = LinkedInBrowserManager()

        self._stop_requested = False
        self._batch_number = 0

    def request_stop(
        self,
        signum: int | None = None,
        frame: Any = None,
    ) -> None:
        """
        Yêu cầu worker dừng an toàn sau thao tác hiện tại.
        """
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

    def run_forever(self) -> int:
        """
        Chạy worker cho tới khi bị dừng.
        """
        self._register_signal_handlers()

        print("")
        print(
            "Starting LinkedIn persistent worker."
        )
        print(
            "Batch size: "
            f"{self.worker_settings.batch_size}/"
            f"{MAX_BATCH_SIZE}"
        )
        print(
            "Idle polling interval: "
            f"{self.worker_settings.idle_poll_seconds} "
            "seconds"
        )
        print(
            "Error retry interval: "
            f"{self.worker_settings.error_retry_seconds} "
            "seconds"
        )
        print(
            "Press Ctrl+C to stop."
        )

        try:
            self.browser.start()

            while not self._stop_requested:
                try:
                    processed_count = (
                        self.run_one_batch()
                    )

                except LinkedInSessionError as exc:
                    print(
                        "",
                        file=sys.stderr,
                    )
                    print(
                        "LinkedIn session requires "
                        "manual attention.",
                        file=sys.stderr,
                    )
                    print(
                        f"{type(exc).__name__}: {exc}",
                        file=sys.stderr,
                    )
                    print(
                        "Worker stopped to avoid "
                        "additional LinkedIn requests.",
                        file=sys.stderr,
                    )

                    return 2

                except Exception as exc:
                    print(
                        "",
                        file=sys.stderr,
                    )
                    print(
                        "Worker batch failed: "
                        f"{type(exc).__name__}: {exc}",
                        file=sys.stderr,
                    )

                    if self._stop_requested:
                        break

                    self._sleep_interruptibly(
                        self.worker_settings
                        .error_retry_seconds
                    )

                    continue

                if self._stop_requested:
                    break

                if processed_count == 0:
                    self._sleep_interruptibly(
                        self.worker_settings
                        .idle_poll_seconds
                    )

                # Nếu vừa xử lý đủ một batch, query ngay
                # batch tiếp theo. Delay từng profile đã
                # được áp dụng trong run_one_batch().

            return 0

        except KeyboardInterrupt:
            self.request_stop()
            return 0

        finally:
            self.browser.stop()

            print("")
            print(
                "LinkedIn worker stopped."
            )

    def run_one_batch(self) -> int:
        """
        Query và xử lý tối đa một batch source pending.

        Trả về số source đã được load trong batch.
        """
        self._batch_number += 1

        sources = get_unscanned_sources(
            settings=self.settings,
            limit=self.worker_settings.batch_size,
        )

        total = len(sources)

        if total == 0:
            print("")
            print(
                "No pending LinkedIn sources. "
                "Waiting for new URLs..."
            )

            return 0

        print("")
        print(
            "=" * 70
        )
        print(
            f"Worker batch {self._batch_number}"
        )
        print(
            f"Pending sources loaded: {total}"
        )

        success_count = 0
        failed_count = 0

        for index, source in enumerate(
            sources,
            start=1,
        ):
            if self._stop_requested:
                break

            source_id = int(
                source["id"]
            )

            linkedin_url = str(
                source.get(
                    "linkedin_url",
                    "",
                )
                or ""
            ).strip()

            print("")
            print(
                "-" * 70
            )
            print(
                f"[{index}/{total}] "
                f"Source ID: {source_id}"
            )
            print(
                f"URL: {linkedin_url}"
            )

            if not linkedin_url:
                failed_count += 1

                print(
                    "Source skipped because "
                    "linkedin_url is empty.",
                    file=sys.stderr,
                )

                self._wait_between_profiles(
                    index=index,
                    total=total,
                )

                continue

            try:
                self._process_source(
                    source_id=source_id,
                )

                success_count += 1

            except LinkedInSessionError:
                raise

            except Exception as exc:
                failed_count += 1

                print(
                    f"Failed source {source_id}: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )

                # Không mark source scanned.
                # Row vẫn last_scanned_at = null
                # để retry trong batch sau.

            self._wait_between_profiles(
                index=index,
                total=total,
            )

        print("")
        print(
            "=" * 70
        )
        print(
            f"Worker batch {self._batch_number} completed."
        )
        print(
            f"Loaded: {total}"
        )
        print(
            f"Success: {success_count}"
        )
        print(
            f"Failed: {failed_count}"
        )

        return total

    def _process_source(
        self,
        *,
        source_id: int,
    ) -> None:
        """
        Scan và persist một source.

        Thứ tự cố định:
        1. Scrape.
        2. Validate source_id.
        3. Lưu JSON local.
        4. Upsert snapshot.
        5. Mark source scanned.

        Không mark scanned nếu bước 3 hoặc 4 lỗi.
        """
        result = scrape_profile_raw(
            settings=self.settings,
            source_id=source_id,
            browser=self.browser,
        )

        result_source_id = int(
            result["source_id"]
        )

        if result_source_id != source_id:
            raise RuntimeError(
                "Scraper returned an unexpected "
                "source_id. "
                f"Expected {source_id}, "
                f"received {result_source_id}."
            )

        scraped_at = str(
            result.get(
                "scraped_at",
                "",
            )
            or ""
        ).strip()

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

        mark_source_scanned(
            settings=self.settings,
            source_id=source_id,
            scanned_at=scraped_at,
        )

        profile = result.get(
            "profile",
            {},
        )

        if not isinstance(
            profile,
            dict,
        ):
            profile = {}

        errors = result.get(
            "errors",
            [],
        )

        if not isinstance(
            errors,
            list,
        ):
            errors = []

        print(
            f"Completed source {source_id}."
        )
        print(
            f"Snapshot ID: {snapshot_id}"
        )
        print(
            f"Name: {profile.get('name', '')}"
        )
        print(
            "Post captions found: "
            f"{get_result_post_count(result)}"
        )
        print(
            f"Section errors: {len(errors)}"
        )
        print(
            f"Output: {output_path.resolve()}"
        )

        if errors:
            print(
                "Section warnings:"
            )

            for error in errors:
                if isinstance(
                    error,
                    dict,
                ):
                    section = (
                        error.get("section")
                        or error.get("stage")
                        or "unknown"
                    )

                    message = str(
                        error.get(
                            "message",
                            "",
                        )
                    )

                    print(
                        f"  - {section}: {message}"
                    )
                else:
                    print(
                        f"  - {error}"
                    )

    def _wait_between_profiles(
        self,
        *,
        index: int,
        total: int,
    ) -> None:
        """
        Delay ngẫu nhiên giữa các profile.

        Không delay sau source cuối của batch.
        """
        if self._stop_requested:
            return

        if index >= total:
            return

        minimum_delay = (
            self.worker_settings
            .minimum_profile_delay_seconds
        )

        maximum_delay = (
            self.worker_settings
            .maximum_profile_delay_seconds
        )

        if maximum_delay <= 0:
            return

        delay_seconds = random.randint(
            minimum_delay,
            maximum_delay,
        )

        print(
            f"Waiting {delay_seconds} seconds "
            "before next profile..."
        )

        self._sleep_interruptibly(
            delay_seconds
        )

    def _sleep_interruptibly(
        self,
        seconds: int,
    ) -> None:
        """
        Sleep theo từng giây để Ctrl+C/SIGTERM dừng nhanh.
        """
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

    def _register_signal_handlers(
        self,
    ) -> None:
        """
        Đăng ký tín hiệu dừng an toàn.
        """
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


def main() -> int:
    try:
        settings = load_settings()

        worker_settings = (
            WorkerSettings.from_environment()
        )

        worker = LinkedInWorker(
            settings=settings,
            worker_settings=worker_settings,
        )

        return worker.run_forever()

    except Exception as exc:
        print(
            "Could not start LinkedIn worker: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
