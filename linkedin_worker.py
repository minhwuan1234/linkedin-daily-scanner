from __future__ import annotations

import os
import random
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.lark_client import (
    LarkClient,
    LarkClientError,
)
from app.linkedin_browser import (
    LinkedInBrowserManager,
    LinkedInSessionError,
)
from app.linkedin_scanner import (
    create_supabase_client,
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
    save_local_output,
)


SOURCE_TABLE = "linkedin_sources"

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


def _clean_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return str(value).strip()


def get_pending_sources(
    *,
    settings: Settings,
    limit: int,
) -> list[dict[str, Any]]:
    """
    Lấy tối đa N profile source đang chờ scan.

    Lấy luôn metadata Lark để worker có thể gửi kết quả
    về đúng chat sau khi scan.
    """
    if limit < 1:
        raise ValueError(
            "limit must be at least 1"
        )

    if limit > MAX_BATCH_SIZE:
        raise ValueError(
            f"limit cannot exceed {MAX_BATCH_SIZE}"
        )

    client = create_supabase_client(
        settings
    )

    response = (
        client
        .table(SOURCE_TABLE)
        .select(
            "id,"
            "name,"
            "linkedin_url,"
            "source_type,"
            "enabled,"
            "last_scanned_at,"
            "lark_chat_id,"
            "lark_message_id,"
            "lark_sender_open_id,"
            "lark_result_sent_at,"
            "lark_result_error"
        )
        .eq(
            "enabled",
            True,
        )
        .eq(
            "source_type",
            "profile",
        )
        .is_(
            "last_scanned_at",
            "null",
        )
        .order(
            "id",
            desc=False,
        )
        .limit(
            limit
        )
        .execute()
    )

    return list(
        response.data or []
    )


def update_lark_delivery_status(
    *,
    settings: Settings,
    source_id: int,
    sent_at: str | None,
    error: str | None,
) -> None:
    """
    Lưu trạng thái gửi kết quả về Lark.

    Gửi thành công:
        lark_result_sent_at = timestamp
        lark_result_error = null

    Gửi lỗi:
        lark_result_sent_at = null
        lark_result_error = error text
    """
    client = create_supabase_client(
        settings
    )

    payload = {
        "lark_result_sent_at": sent_at,
        "lark_result_error": error,
    }

    response = (
        client
        .table(SOURCE_TABLE)
        .update(
            payload
        )
        .eq(
            "id",
            int(source_id),
        )
        .execute()
    )

    if response.data is None:
        raise RuntimeError(
            "Could not update Lark delivery status "
            f"for source {source_id}"
        )


def build_lark_result_message(
    *,
    source: dict[str, Any],
    result: dict[str, Any],
    snapshot_id: int,
) -> str:
    """
    Tạo message kết quả gửi về Lark.

    Chỉ gửi summary, không gửi toàn bộ raw profile data.
    """
    source_id = int(
        result["source_id"]
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

    name = (
        _clean_text(
            profile.get("name")
        )
        or _clean_text(
            source.get("name")
        )
        or "Unknown"
    )

    headline = (
        _clean_text(
            profile.get("headline")
        )
        or "Not found"
    )

    location = (
        _clean_text(
            profile.get("location")
        )
        or "Not found"
    )

    linkedin_url = (
        _clean_text(
            profile.get("linkedin_url")
        )
        or _clean_text(
            source.get("linkedin_url")
        )
    )

    captions = result.get(
        "recent_post_captions",
        [],
    )

    if not isinstance(
        captions,
        list,
    ):
        captions = []

    errors = result.get(
        "errors",
        [],
    )

    if not isinstance(
        errors,
        list,
    ):
        errors = []

    lines = [
        "LinkedIn scan completed",
        "",
        f"Name: {name}",
        f"Headline: {headline}",
        f"Location: {location}",
        f"Recent post captions: {len(captions)}",
        f"Source ID: {source_id}",
        f"Snapshot ID: {snapshot_id}",
        "Status: Saved successfully",
    ]

    if linkedin_url:
        lines.append(
            f"LinkedIn: {linkedin_url}"
        )

    if errors:
        lines.append(
            f"Section warnings: {len(errors)}"
        )

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
            caption_text = _clean_text(
                caption
            )

            caption_preview = (
                caption_text.replace(
                    "\n",
                    " ",
                )
            )

            if len(caption_preview) > 300:
                caption_preview = (
                    caption_preview[:297]
                    + "..."
                )

            lines.append(
                f"{index}. {caption_preview}"
            )

    return "\n".join(lines)


def build_lark_failure_message(
    *,
    source: dict[str, Any],
    error: Exception,
) -> str:
    """
    Tạo message báo lỗi scan.

    Hiện worker chỉ dùng hàm này khi còn đủ thông tin
    để gửi về chat.
    """
    source_id = source.get(
        "id",
        "unknown",
    )

    linkedin_url = _clean_text(
        source.get("linkedin_url")
    )

    lines = [
        "LinkedIn scan failed",
        "",
        f"Source ID: {source_id}",
        (
            "Error: "
            f"{type(error).__name__}: {error}"
        ),
    ]

    if linkedin_url:
        lines.insert(
            2,
            f"LinkedIn: {linkedin_url}",
        )

    return "\n".join(lines)


class LinkedInWorker:
    """
    Worker chạy liên tục trên Mac.

    Một browser persistent dùng chung cho nhiều source và
    nhiều batch.

    Browser chỉ đóng khi:
    - Ctrl+C
    - SIGTERM
    - LinkedIn login/checkpoint
    - process dừng
    """

    def __init__(
        self,
        *,
        settings: Settings,
        worker_settings: WorkerSettings,
    ) -> None:
        self.settings = settings
        self.worker_settings = worker_settings

        self.browser = (
            LinkedInBrowserManager()
        )

        self.lark_client: (
            LarkClient | None
        ) = None

        self._stop_requested = False
        self._batch_number = 0

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

    def run_forever(self) -> int:
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

            # Chỉ khởi tạo Lark client một lần.
            # Token sẽ được cache trong process.
            try:
                self.lark_client = LarkClient()

                print(
                    "Lark outbound client: ready"
                )

            except Exception as exc:
                self.lark_client = None

                print(
                    "Lark outbound client unavailable: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )

                print(
                    "Worker will continue scanning, "
                    "but cannot send results to Lark.",
                    file=sys.stderr,
                )

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
        self._batch_number += 1

        sources = get_pending_sources(
            settings=self.settings,
            limit=(
                self.worker_settings
                .batch_size
            ),
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

            linkedin_url = _clean_text(
                source.get(
                    "linkedin_url"
                )
            )

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
                    source=source,
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

                self._try_send_failure_message(
                    source=source,
                    error=exc,
                )

                # Không mark source scanned nếu profile
                # scan hoặc snapshot save thất bại.

            self._wait_between_profiles(
                index=index,
                total=total,
            )

        print("")
        print(
            "=" * 70
        )
        print(
            f"Worker batch "
            f"{self._batch_number} completed."
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
        source: dict[str, Any],
    ) -> None:
        """
        Scan và lưu một source.

        Thứ tự:
        1. Scrape.
        2. Lưu JSON local.
        3. Upsert snapshot.
        4. Mark source scanned.
        5. Gửi kết quả Lark.
        6. Ghi trạng thái gửi Lark.

        Lark lỗi không làm mất kết quả scan.
        """
        source_id = int(
            source["id"]
        )

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

        scraped_at = _clean_text(
            result.get(
                "scraped_at"
            )
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

        # Sau bước này profile không cần scan lại,
        # kể cả Lark gửi message thất bại.
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

        self._send_success_message(
            source=source,
            result=result,
            snapshot_id=snapshot_id,
        )

    def _send_success_message(
        self,
        *,
        source: dict[str, Any],
        result: dict[str, Any],
        snapshot_id: int,
    ) -> None:
        source_id = int(
            source["id"]
        )

        chat_id = _clean_text(
            source.get(
                "lark_chat_id"
            )
        )

        if not chat_id:
            print(
                "Lark result skipped: "
                "source has no lark_chat_id."
            )

            return

        if self.lark_client is None:
            error_message = (
                "Lark client is not available."
            )

            self._record_lark_error(
                source_id=source_id,
                error_message=error_message,
            )

            print(
                f"Lark result failed: {error_message}",
                file=sys.stderr,
            )

            return

        message_text = (
            build_lark_result_message(
                source=source,
                result=result,
                snapshot_id=snapshot_id,
            )
        )

        deduplication_key = (
            f"linkedin-result:"
            f"{source_id}:"
            f"{result.get('scraped_at', '')}"
        )

        try:
            message_result = (
                self.lark_client
                .send_text_to_chat(
                    chat_id=chat_id,
                    text=message_text,
                    deduplication_key=(
                        deduplication_key
                    ),
                )
            )

            sent_at = datetime.now(
                timezone.utc
            ).isoformat()

            update_lark_delivery_status(
                settings=self.settings,
                source_id=source_id,
                sent_at=sent_at,
                error=None,
            )

            print(
                "Lark result sent successfully."
            )
            print(
                "Lark outbound message ID: "
                f"{message_result.message_id}"
            )

        except Exception as exc:
            error_message = (
                f"{type(exc).__name__}: {exc}"
            )

            self._record_lark_error(
                source_id=source_id,
                error_message=error_message,
            )

            print(
                "Profile was saved, but Lark "
                "result delivery failed: "
                f"{error_message}",
                file=sys.stderr,
            )

    def _try_send_failure_message(
        self,
        *,
        source: dict[str, Any],
        error: Exception,
    ) -> None:
        """
        Cố gửi thông báo scan lỗi.

        Không raise thêm lỗi nếu Lark cũng đang lỗi.
        """
        source_id_raw = source.get(
            "id"
        )

        if source_id_raw is None:
            return

        source_id = int(
            source_id_raw
        )

        chat_id = _clean_text(
            source.get(
                "lark_chat_id"
            )
        )

        if not chat_id:
            return

        if self.lark_client is None:
            return

        message_text = (
            build_lark_failure_message(
                source=source,
                error=error,
            )
        )

        deduplication_key = (
            f"linkedin-failure:"
            f"{source_id}:"
            f"{source.get('lark_message_id', '')}"
        )

        try:
            self.lark_client.send_text_to_chat(
                chat_id=chat_id,
                text=message_text,
                deduplication_key=(
                    deduplication_key
                ),
            )

            print(
                "Lark failure notification sent."
            )

        except Exception as lark_exc:
            print(
                "Could not send Lark failure "
                "notification: "
                f"{type(lark_exc).__name__}: "
                f"{lark_exc}",
                file=sys.stderr,
            )

    def _record_lark_error(
        self,
        *,
        source_id: int,
        error_message: str,
    ) -> None:
        """
        Lưu lỗi gửi Lark mà không làm worker crash.
        """
        safe_error = (
            error_message[:2000]
        )

        try:
            update_lark_delivery_status(
                settings=self.settings,
                source_id=source_id,
                sent_at=None,
                error=safe_error,
            )

        except Exception as status_exc:
            print(
                "Could not save Lark delivery error: "
                f"{type(status_exc).__name__}: "
                f"{status_exc}",
                file=sys.stderr,
            )

    def _wait_between_profiles(
        self,
        *,
        index: int,
        total: int,
    ) -> None:
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
