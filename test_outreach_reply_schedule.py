from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from app.outreach_reply_schedule import (
    VIETNAM_TIMEZONE,
    next_reply_check_at,
    run_reply_check_schedule,
)


class ReplyCheckScheduleTests(unittest.TestCase):
    def test_morning_goes_to_noon(self) -> None:
        now = datetime(2026, 9, 24, 11, 59, tzinfo=VIETNAM_TIMEZONE)
        self.assertEqual(
            next_reply_check_at(now),
            datetime(2026, 9, 24, 12, 0, tzinfo=VIETNAM_TIMEZONE),
        )

    def test_noon_goes_to_evening(self) -> None:
        now = datetime(2026, 9, 24, 5, 0, tzinfo=timezone.utc)
        self.assertEqual(
            next_reply_check_at(now),
            datetime(2026, 9, 24, 18, 0, tzinfo=VIETNAM_TIMEZONE),
        )

    def test_evening_goes_to_next_day(self) -> None:
        now = datetime(2026, 9, 24, 18, 1, tzinfo=VIETNAM_TIMEZONE)
        self.assertEqual(
            next_reply_check_at(now),
            datetime(2026, 9, 25, 12, 0, tzinfo=VIETNAM_TIMEZONE),
        )

    def test_naive_datetime_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            next_reply_check_at(datetime(2026, 9, 24, 12, 0))

    def test_loop_waits_until_slot(self) -> None:
        current = datetime(2026, 9, 24, 4, 59, tzinfo=timezone.utc)
        scans: list[datetime] = []

        def now() -> datetime:
            return current

        def sleep(seconds: float) -> None:
            nonlocal current
            current += timedelta(seconds=seconds)

        def scan() -> None:
            scans.append(current)
            raise StopIteration

        with self.assertRaises(StopIteration):
            run_reply_check_schedule(scan, now=now, sleep=sleep)

        self.assertEqual(scans, [datetime(2026, 9, 24, 5, 0, tzinfo=timezone.utc)])


if __name__ == "__main__":
    unittest.main()
