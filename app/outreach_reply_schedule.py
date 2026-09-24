"""Vietnam-time schedule for the dedicated Outreach reply-check worker."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


VIETNAM_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
REPLY_CHECK_HOURS = (12, 18)

logger = logging.getLogger("outreach_reply_schedule")


def next_reply_check_at(now: datetime) -> datetime:
    """Return the next 12:00 or 18:00 Vietnam-time slot after ``now``."""

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    local_now = now.astimezone(VIETNAM_TIMEZONE)
    for day_offset in (0, 1):
        day = (local_now + timedelta(days=day_offset)).date()
        for hour in REPLY_CHECK_HOURS:
            candidate = datetime(
                day.year, day.month, day.day, hour, 0,
                tzinfo=VIETNAM_TIMEZONE,
            )
            if candidate > local_now:
                return candidate

    raise AssertionError("A reply-check slot must exist within the next day")


def run_reply_check_schedule(
    scan_all_accounts: Callable[[], None],
    *,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Wait for each slot without drifting when a scan takes time."""

    while True:
        slot = next_reply_check_at(now())
        logger.info("Next reply check: %s", slot.isoformat())
        while True:
            seconds_left = (slot - now()).total_seconds()
            if seconds_left <= 0:
                break
            sleep(min(seconds_left, 60.0))

        logger.info("Starting scheduled reply check: %s", slot.isoformat())
        scan_all_accounts()
