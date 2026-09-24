"""Read live Outreach tasks for the dashboard header."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from supabase import Client

from app.outreach_dashboard_store import get_outreach_client


ACTIVE_WINDOW = timedelta(minutes=30)
REPLY_SCAN_WINDOW = timedelta(minutes=2)

TASKS = (
    ("connect", "Connect", "outreach_jobs", "running", "job_code", "updated_at"),
    ("acceptance", "Acceptance check", "outreach_acceptance_checks", "running", "source_job_id", "updated_at"),
    ("messages", "Message sending", "outreach_message_batches", "processing", "batch_code", "updated_at"),
    ("reply_send", "Reply sending", "outreach_reply_send_jobs", "processing", "user_name", "updated_at"),
    ("sessions", "Login session check", "outreach_account_sessions", "checking", "display_name", "updated_at"),
)


def _recent(value: object, window: timedelta, now: datetime) -> bool:
    if not value:
        return False
    try:
        timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return timestamp.tzinfo is not None and now - window <= timestamp <= now + timedelta(minutes=1)
    except (TypeError, ValueError):
        return False


def _rows(client: Client, table: str, status: str, fields: str) -> list[dict]:
    response = (
        client.table(table)
        .select(fields)
        .eq("status", status)
        .limit(100)
        .execute()
    )
    return list(response.data or [])


def get_outreach_worker_activity(*, client: Client | None = None) -> dict:
    active_client = client or get_outreach_client()
    now = datetime.now(timezone.utc)
    tasks = []
    errors = []

    for key, label, table, status, detail_field, time_field in TASKS:
        try:
            records = _rows(active_client, table, status, f"{detail_field},{time_field}")
            active = [row for row in records if _recent(row.get(time_field), ACTIVE_WINDOW, now)]
            tasks.append({
                "key": key,
                "label": label,
                "count": len(active),
                "details": [str(row.get(detail_field) or "").strip() for row in active[:3]],
            })
        except Exception:
            errors.append(key)
            tasks.append({"key": key, "label": label, "count": None, "details": []})

    # Reply scans have no job row; they report a short-lived heartbeat in the
    # optional activity table installed by outreach_worker_activity.sql.
    try:
        records = _rows(active_client, "outreach_worker_activity", "running", "task_key,account_id,updated_at")
        active = [
            row for row in records
            if row.get("task_key") == "reply_check"
            and _recent(row.get("updated_at"), REPLY_SCAN_WINDOW, now)
        ]
        tasks.append({
            "key": "reply_check", "label": "Reply checking", "count": len(active),
            "details": [str(row.get("account_id") or "").strip() for row in active[:3]],
        })
    except Exception:
        errors.append("reply_check")
        tasks.append({"key": "reply_check", "label": "Reply checking", "count": None, "details": []})

    return {
        "tasks": tasks,
        "active_count": sum(task["count"] or 0 for task in tasks),
        "complete": not errors,
        "checked_at": now.isoformat(),
    }
