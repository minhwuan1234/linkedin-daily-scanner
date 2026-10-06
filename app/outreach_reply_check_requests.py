"""Small Supabase queue for dashboard-triggered reply scans."""

from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client

from app.outreach_dashboard_store import get_outreach_client


TABLE = "outreach_reply_check_requests"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def request_reply_check(*, client: Client | None = None) -> dict:
    active_client = client or get_outreach_client()
    active = (
        active_client.table(TABLE)
        .select("id,status,requested_at")
        .in_("status", ["queued", "running"])
        .order("requested_at")
        .limit(1)
        .execute()
    )
    if active.data:
        return {**dict(active.data[0]), "already_active": True}
    response = active_client.table(TABLE).insert({"status": "queued"}).execute()
    rows = list(response.data or [])
    if not rows:
        raise RuntimeError("Could not queue the reply check request.")
    return {**dict(rows[0]), "already_active": False}


def get_reply_check_request(request_id: str, *, client: Client | None = None) -> dict | None:
    response = (
        (client or get_outreach_client()).table(TABLE)
        .select("id,status,requested_at,started_at,finished_at,error")
        .eq("id", request_id)
        .limit(1)
        .execute()
    )
    return dict(response.data[0]) if response.data else None


def get_latest_completed_reply_check(*, client: Client | None = None) -> dict | None:
    response = (
        (client or get_outreach_client()).table(TABLE)
        .select("id,started_at,finished_at")
        .eq("status", "completed")
        .order("finished_at", desc=True)
        .limit(1)
        .execute()
    )
    return dict(response.data[0]) if response.data else None


def record_scheduled_reply_check(
    started_at: str,
    *,
    error: str | None = None,
    client: Client | None = None,
) -> dict:
    response = (
        (client or get_outreach_client()).table(TABLE)
        .insert({
            "status": "failed" if error else "completed",
            "requested_at": started_at,
            "started_at": started_at,
            "finished_at": _now(),
            "error": str(error)[:1000] if error else None,
        })
        .execute()
    )
    rows = list(response.data or [])
    if not rows:
        raise RuntimeError("Could not record scheduled reply-check completion.")
    return dict(rows[0])


def claim_reply_check_request(*, client: Client | None = None) -> dict | None:
    active_client = client or get_outreach_client()
    queued = (
        active_client.table(TABLE)
        .select("id")
        .eq("status", "queued")
        .order("requested_at")
        .limit(1)
        .execute()
    )
    if not queued.data:
        return None
    request_id = str(queued.data[0]["id"])
    claimed = (
        active_client.table(TABLE)
        .update({"status": "running", "started_at": _now()})
        .eq("id", request_id)
        .eq("status", "queued")
        .execute()
    )
    return dict(claimed.data[0]) if claimed.data else None


def finish_reply_check_request(
    request_id: str,
    *,
    error: str | None = None,
    client: Client | None = None,
) -> None:
    now = _now()
    (client or get_outreach_client()).table(TABLE).update({
        "status": "failed" if error else "completed",
        "finished_at": now,
        "error": (str(error)[:1000] if error else None),
    }).eq("id", request_id).eq("status", "running").execute()
