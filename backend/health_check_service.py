from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.linkedin_scanner import create_supabase_client
from app.settings import Settings


SOURCE_TABLE = "linkedin_sources"
ACCOUNT_TABLE = "linkedin_scanner_accounts"
WORKER_HEALTH_TABLE = "linkedin_worker_health"

DEFAULT_WORKER_STALE_SECONDS = 90
DEFAULT_JOB_STALE_MINUTES = 20


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(
    value: Any,
) -> datetime | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    try:
        parsed = datetime.fromisoformat(
            text.replace("Z", "+00:00")
        )
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed.astimezone(
        timezone.utc
    )


def _seconds_since(
    value: Any,
) -> int | None:
    parsed = _parse_datetime(value)

    if parsed is None:
        return None

    seconds = int(
        (_utc_now() - parsed).total_seconds()
    )

    return max(0, seconds)


def _format_age(
    seconds: int | None,
) -> str:
    if seconds is None:
        return "unknown"

    if seconds < 60:
        return f"{seconds}s ago"

    minutes = seconds // 60

    if minutes < 60:
        return f"{minutes}m ago"

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if hours < 24:
        return (
            f"{hours}h {remaining_minutes}m ago"
        )

    days = hours // 24
    remaining_hours = hours % 24

    return (
        f"{days}d {remaining_hours}h ago"
    )


def _safe_int(
    value: Any,
    *,
    default: int = 0,
) -> int:
    try:
        return int(value)
    except (
        TypeError,
        ValueError,
    ):
        return default


@dataclass(frozen=True)
class HealthCheckResult:
    overall_status: str
    message: str
    details: dict[str, Any]


class LinkedInSystemHealthCheck:
    """
    Read-only health check for the whole LinkedIn scanner.

    It reads the existing shared Supabase database:
    - linkedin_sources
    - linkedin_scanner_accounts
    - linkedin_worker_health

    It does not scan LinkedIn.
    It does not modify jobs.
    It does not create a new database.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        worker_stale_seconds: int = (
            DEFAULT_WORKER_STALE_SECONDS
        ),
        job_stale_minutes: int = (
            DEFAULT_JOB_STALE_MINUTES
        ),
    ) -> None:
        if worker_stale_seconds < 30:
            raise ValueError(
                "worker_stale_seconds must be "
                "at least 30"
            )

        if job_stale_minutes < 1:
            raise ValueError(
                "job_stale_minutes must be "
                "at least 1"
            )

        self.client = create_supabase_client(
            settings
        )

        self.worker_stale_seconds = (
            worker_stale_seconds
        )

        self.job_stale_minutes = (
            job_stale_minutes
        )

    def run(
        self,
    ) -> HealthCheckResult:
        database_error: str | None = None

        try:
            queue_counts = (
                self._get_queue_counts()
            )
            accounts = self._get_accounts()
            worker = self._get_latest_worker()
            stale_jobs = (
                self._get_stale_job_count()
            )
            unsent_results = (
                self._get_unsent_lark_count()
            )
            last_scan_at = (
                self._get_last_scan_at()
            )

        except Exception as exc:
            database_error = (
                f"{type(exc).__name__}: {exc}"
            )

            queue_counts = {
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0,
                "disabled": 0,
            }
            accounts = []
            worker = None
            stale_jobs = 0
            unsent_results = 0
            last_scan_at = None

        details = self._build_details(
            database_error=database_error,
            queue_counts=queue_counts,
            accounts=accounts,
            worker=worker,
            stale_jobs=stale_jobs,
            unsent_results=unsent_results,
            last_scan_at=last_scan_at,
        )

        overall_status = (
            self._resolve_overall_status(
                details
            )
        )

        message = self._build_message(
            overall_status=overall_status,
            details=details,
        )

        return HealthCheckResult(
            overall_status=overall_status,
            message=message,
            details=details,
        )

    def _get_queue_counts(
        self,
    ) -> dict[str, int]:
        statuses = (
            "pending",
            "processing",
            "completed",
            "failed",
            "disabled",
        )

        counts: dict[str, int] = {}

        for status in statuses:
            response = (
                self.client
                .table(SOURCE_TABLE)
                .select(
                    "id",
                    count="exact",
                )
                .eq(
                    "job_status",
                    status,
                )
                .limit(1)
                .execute()
            )

            counts[status] = _safe_int(
                response.count
            )

        return counts

    def _get_accounts(
        self,
    ) -> list[dict[str, Any]]:
        response = (
            self.client
            .table(ACCOUNT_TABLE)
            .select(
                "account_id,status,enabled,"
                "current_source_id,"
                "consecutive_failures,"
                "last_used_at,last_success_at,"
                "last_error,cooldown_until"
            )
            .order(
                "account_id"
            )
            .execute()
        )

        return [
            dict(row)
            for row in list(
                response.data or []
            )
            if isinstance(row, dict)
        ]

    def _get_latest_worker(
        self,
    ) -> dict[str, Any] | None:
        response = (
            self.client
            .table(WORKER_HEALTH_TABLE)
            .select(
                "worker_id,worker_name,status,"
                "worker_version,hostname,pid,"
                "current_account_id,"
                "current_source_id,"
                "last_heartbeat_at,"
                "last_success_at,last_error"
            )
            .order(
                "last_heartbeat_at",
                desc=True,
            )
            .limit(1)
            .execute()
        )

        rows = list(
            response.data or []
        )

        if not rows:
            return None

        row = rows[0]

        if not isinstance(row, dict):
            return None

        return dict(row)

    def _get_stale_job_count(
        self,
    ) -> int:
        cutoff = (
            _utc_now().timestamp()
            - (
                self.job_stale_minutes
                * 60
            )
        )

        cutoff_iso = datetime.fromtimestamp(
            cutoff,
            tz=timezone.utc,
        ).isoformat()

        response = (
            self.client
            .table(SOURCE_TABLE)
            .select(
                "id",
                count="exact",
            )
            .eq(
                "job_status",
                "processing",
            )
            .lt(
                "processing_heartbeat_at",
                cutoff_iso,
            )
            .limit(1)
            .execute()
        )

        return _safe_int(
            response.count
        )

    def _get_unsent_lark_count(
        self,
    ) -> int:
        response = (
            self.client
            .table(SOURCE_TABLE)
            .select(
                "id",
                count="exact",
            )
            .not_.is_(
                "lark_chat_id",
                "null",
            )
            .not_.is_(
                "last_scanned_at",
                "null",
            )
            .is_(
                "lark_result_sent_at",
                "null",
            )
            .limit(1)
            .execute()
        )

        return _safe_int(
            response.count
        )

    def _get_last_scan_at(
        self,
    ) -> str | None:
        response = (
            self.client
            .table(SOURCE_TABLE)
            .select(
                "last_scanned_at"
            )
            .not_.is_(
                "last_scanned_at",
                "null",
            )
            .order(
                "last_scanned_at",
                desc=True,
            )
            .limit(1)
            .execute()
        )

        rows = list(
            response.data or []
        )

        if not rows:
            return None

        return str(
            rows[0].get(
                "last_scanned_at"
            )
            or ""
        ).strip() or None

    def _build_details(
        self,
        *,
        database_error: str | None,
        queue_counts: dict[str, int],
        accounts: list[dict[str, Any]],
        worker: dict[str, Any] | None,
        stale_jobs: int,
        unsent_results: int,
        last_scan_at: str | None,
    ) -> dict[str, Any]:
        worker_heartbeat_age = None
        worker_online = False

        if worker is not None:
            worker_heartbeat_age = (
                _seconds_since(
                    worker.get(
                        "last_heartbeat_at"
                    )
                )
            )

            worker_online = (
                worker_heartbeat_age is not None
                and worker_heartbeat_age
                <= self.worker_stale_seconds
                and worker.get("status")
                not in (
                    "offline",
                    "stopping",
                )
            )

        enabled_accounts = [
            account
            for account in accounts
            if account.get("enabled") is True
        ]

        needs_login_accounts = [
            str(account.get("account_id"))
            for account in enabled_accounts
            if account.get("status")
            == "needs_login"
        ]

        error_accounts = [
            str(account.get("account_id"))
            for account in enabled_accounts
            if account.get("status")
            == "error"
        ]

        return {
            "database_healthy": (
                database_error is None
            ),
            "database_error": database_error,
            "worker": worker,
            "worker_online": worker_online,
            "worker_heartbeat_age_seconds": (
                worker_heartbeat_age
            ),
            "queue_counts": queue_counts,
            "accounts": accounts,
            "enabled_account_count": len(
                enabled_accounts
            ),
            "needs_login_accounts": (
                needs_login_accounts
            ),
            "error_accounts": error_accounts,
            "stale_job_count": stale_jobs,
            "unsent_lark_result_count": (
                unsent_results
            ),
            "last_scan_at": last_scan_at,
            "last_scan_age_seconds": (
                _seconds_since(last_scan_at)
            ),
        }

    def _resolve_overall_status(
        self,
        details: dict[str, Any],
    ) -> str:
        if not details["database_healthy"]:
            return "UNHEALTHY"

        if not details["worker_online"]:
            return "UNHEALTHY"

        if details["enabled_account_count"] == 0:
            return "UNHEALTHY"

        degraded = any(
            (
                details["stale_job_count"] > 0,
                details[
                    "unsent_lark_result_count"
                ] > 0,
                bool(
                    details[
                        "needs_login_accounts"
                    ]
                ),
                bool(
                    details["error_accounts"]
                ),
                details[
                    "queue_counts"
                ].get(
                    "failed",
                    0,
                ) > 0,
            )
        )

        return (
            "DEGRADED"
            if degraded
            else "HEALTHY"
        )

    def _build_message(
        self,
        *,
        overall_status: str,
        details: dict[str, Any],
    ) -> str:
        queue = details["queue_counts"]
        worker = details["worker"]

        lines = [
            "LinkedIn Scanner Health Check",
            "",
            f"Overall: {overall_status}",
            "",
        ]

        if details["database_healthy"]:
            lines.append(
                "Supabase: Healthy"
            )
        else:
            lines.append(
                "Supabase: Unhealthy"
            )
            lines.append(
                "Database error: "
                f"{details['database_error']}"
            )

        if worker is None:
            lines.append(
                "Mac Worker: Not registered"
            )
        else:
            worker_state = (
                "Online"
                if details["worker_online"]
                else "Offline or stale"
            )

            lines.extend(
                [
                    f"Mac Worker: {worker_state}",
                    (
                        "Worker status: "
                        f"{worker.get('status') or 'unknown'}"
                    ),
                    (
                        "Last heartbeat: "
                        f"{_format_age(details['worker_heartbeat_age_seconds'])}"
                    ),
                    (
                        "Current account: "
                        f"{worker.get('current_account_id') or '-'}"
                    ),
                    (
                        "Current source: "
                        f"{worker.get('current_source_id') or '-'}"
                    ),
                ]
            )

        lines.extend(
            [
                "",
                "Queue:",
                f"Pending: {queue.get('pending', 0)}",
                (
                    "Processing: "
                    f"{queue.get('processing', 0)}"
                ),
                (
                    "Completed: "
                    f"{queue.get('completed', 0)}"
                ),
                f"Failed: {queue.get('failed', 0)}",
                (
                    "Stale processing: "
                    f"{details['stale_job_count']}"
                ),
                (
                    "Unsent Lark results: "
                    f"{details['unsent_lark_result_count']}"
                ),
                "",
                "LinkedIn Accounts:",
            ]
        )

        accounts = details["accounts"]

        if not accounts:
            lines.append(
                "No account records found"
            )
        else:
            for account in accounts:
                account_id = (
                    account.get("account_id")
                    or "unknown"
                )

                status = (
                    account.get("status")
                    or "unknown"
                )

                enabled = (
                    "enabled"
                    if account.get("enabled") is True
                    else "disabled"
                )

                lines.append(
                    f"{account_id}: "
                    f"{status} ({enabled})"
                )

        lines.extend(
            [
                "",
                (
                    "Last successful scan: "
                    f"{_format_age(details['last_scan_age_seconds'])}"
                ),
            ]
        )

        actions: list[str] = []

        if not details["worker_online"]:
            actions.append(
                "Restart the Mac worker."
            )

        if details["needs_login_accounts"]:
            actions.append(
                "Login again for: "
                + ", ".join(
                    details[
                        "needs_login_accounts"
                    ]
                )
                + "."
            )

        if details["stale_job_count"] > 0:
            actions.append(
                "Release stale processing jobs."
            )

        if (
            details[
                "unsent_lark_result_count"
            ] > 0
        ):
            actions.append(
                "Retry unsent Lark results."
            )

        if actions:
            lines.extend(
                [
                    "",
                    "Action required:",
                    *actions,
                ]
            )

        return "\n".join(lines)
