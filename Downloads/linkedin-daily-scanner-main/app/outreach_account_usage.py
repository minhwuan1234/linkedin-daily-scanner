from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from supabase import Client, create_client

from app.settings import Settings


USAGE_TABLE = "outreach_account_usage"

WEEKLY_SUCCESS_LIMIT = 100

LOCAL_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


@dataclass(frozen=True)
class OutreachAccountUsage:
    account_id: str
    daily_success_count: int
    daily_limit: int
    weekly_success_count: int
    weekly_limit: int
    daily_date: str
    week_start: str

    @property
    def daily_remaining(self) -> int:
        return max(
            self.daily_limit
            - self.daily_success_count,
            0,
        )

    @property
    def weekly_remaining(self) -> int:
        return max(
            self.weekly_limit
            - self.weekly_success_count,
            0,
        )

    @property
    def remaining(self) -> int:
        return self.weekly_remaining

    @property
    def is_available(self) -> bool:
        return self.weekly_remaining > 0


def _utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def _local_today_and_week_start() -> tuple[str, str]:
    now = datetime.now(
        LOCAL_TIMEZONE
    )

    today = now.date()

    monday = (
        today
        .fromordinal(
            today.toordinal()
            - today.weekday()
        )
    )

    return (
        today.isoformat(),
        monday.isoformat(),
    )


class OutreachAccountUsageStore:
    """
    Persistent daily/weekly quota store.

    Chỉ tăng quota khi result.status == "invitation_sent".

    Weekly:
        100 invitation_sent / account / Monday-Sunday week.

    Daily count vẫn được giữ trong DB để tương thích dữ liệu cũ,
    nhưng KHÔNG còn dùng làm limit.

    Reset không cần cron:
    - sang tuần mới -> weekly count tự reset.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        client: Client | None = None,
    ) -> None:
        self.settings = settings

        self.client = (
            client
            if client is not None
            else create_client(
                settings.outreach_supabase_url,
                settings.outreach_supabase_secret_key,
            )
        )

    def _load_row(
        self,
        *,
        account_id: str,
    ) -> dict | None:
        response = (
            self.client
            .table(USAGE_TABLE)
            .select(
                (
                    "account_id,"
                    "daily_success_count,"
                    "daily_date,"
                    "weekly_success_count,"
                    "week_start,"
                    "updated_at"
                )
            )
            .eq(
                "account_id",
                account_id,
            )
            .limit(1)
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

        if not rows:
            return None

        return rows[0]

    def get_usage(
        self,
        *,
        account_id: str,
    ) -> OutreachAccountUsage:
        cleaned_account_id = str(
            account_id or ""
        ).strip()

        if not cleaned_account_id:
            raise ValueError(
                "account_id is required"
            )

        today, week_start = (
            _local_today_and_week_start()
        )

        row = self._load_row(
            account_id=cleaned_account_id
        )

        if row is None:
            daily_success_count = 0
            weekly_success_count = 0
        else:
            daily_success_count = int(
                row.get(
                    "daily_success_count",
                    0,
                )
                or 0
            )

            weekly_success_count = int(
                row.get(
                    "weekly_success_count",
                    0,
                )
                or 0
            )

            stored_daily_date = str(
                row.get(
                    "daily_date",
                    "",
                )
                or ""
            )

            stored_week_start = str(
                row.get(
                    "week_start",
                    "",
                )
                or ""
            )

            if stored_daily_date != today:
                daily_success_count = 0

            if stored_week_start != week_start:
                weekly_success_count = 0

        # Always upsert normalized/reset state so restart is deterministic.
        self._save(
            account_id=cleaned_account_id,
            daily_success_count=daily_success_count,
            daily_date=today,
            weekly_success_count=weekly_success_count,
            week_start=week_start,
        )

        return OutreachAccountUsage(
            account_id=cleaned_account_id,
            daily_success_count=(
                daily_success_count
            ),
            daily_limit=0,
            weekly_success_count=(
                weekly_success_count
            ),
            weekly_limit=WEEKLY_SUCCESS_LIMIT,
            daily_date=today,
            week_start=week_start,
        )

    def _save(
        self,
        *,
        account_id: str,
        daily_success_count: int,
        daily_date: str,
        weekly_success_count: int,
        week_start: str,
    ) -> None:
        payload = {
            "account_id": account_id,
            "daily_success_count": int(
                daily_success_count
            ),
            "daily_date": daily_date,
            "weekly_success_count": int(
                weekly_success_count
            ),
            "week_start": week_start,
            "updated_at": _utc_now_iso(),
        }

        (
            self.client
            .table(USAGE_TABLE)
            .upsert(
                payload,
                on_conflict="account_id",
            )
            .execute()
        )

    def record_invitation_sent(
        self,
        *,
        account_id: str,
    ) -> OutreachAccountUsage:
        usage = self.get_usage(
            account_id=account_id
        )

        if not usage.is_available:
            raise RuntimeError(
                (
                    f"{account_id} has no remaining weekly Connect quota"
                )
            )

        new_daily = (
            usage.daily_success_count + 1
        )

        new_weekly = (
            usage.weekly_success_count + 1
        )

        if new_weekly > WEEKLY_SUCCESS_LIMIT:
            raise RuntimeError(
                (
                    f"{account_id} weekly Connect "
                    "limit would be exceeded"
                )
            )

        self._save(
            account_id=account_id,
            daily_success_count=new_daily,
            daily_date=usage.daily_date,
            weekly_success_count=new_weekly,
            week_start=usage.week_start,
        )

        return OutreachAccountUsage(
            account_id=account_id,
            daily_success_count=new_daily,
            daily_limit=0,
            weekly_success_count=new_weekly,
            weekly_limit=WEEKLY_SUCCESS_LIMIT,
            daily_date=usage.daily_date,
            week_start=usage.week_start,
        )
