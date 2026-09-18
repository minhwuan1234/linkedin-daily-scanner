from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client

from app.outreach_dashboard_store import get_outreach_client


REPLY_TABLE = "outreach_reply_messages"
REPLY_SEND_TABLE = "outreach_reply_send_jobs"


class OutreachReplySendStoreError(RuntimeError):
    pass


def _safe_text(value) -> str:
    return str(value or "").strip()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_reply_send_jobs(
    reply_ids: list[str],
    *,
    client: Client | None = None,
) -> dict[str, dict]:
    cleaned_ids = [value for value in map(_safe_text, reply_ids) if value]
    if not cleaned_ids:
        return {}

    active_client = client or get_outreach_client()
    response = (
        active_client.table(REPLY_SEND_TABLE)
        .select(
            "id,reply_id,assigned_account_id,message_text,status,"
            "prepared_at,queued_at,started_at,sent_at,failed_at,last_error"
        )
        .in_("reply_id", cleaned_ids)
        .execute()
    )
    return {
        _safe_text(row.get("reply_id")): dict(row)
        for row in list(response.data or [])
    }


def prepare_reply_send(
    *,
    reply_id: str,
    message_text: str,
    client: Client | None = None,
) -> dict:
    cleaned_reply_id = _safe_text(reply_id)
    cleaned_message = str(message_text or "").strip()
    if not cleaned_reply_id:
        raise OutreachReplySendStoreError("reply_id is required.")
    if not cleaned_message:
        raise OutreachReplySendStoreError("message_text is required.")

    active_client = client or get_outreach_client()
    reply_response = (
        active_client.table(REPLY_TABLE)
        .select("id,sent_target_id,assigned_account_id,user_name,linkedin_url")
        .eq("id", cleaned_reply_id)
        .limit(1)
        .execute()
    )
    reply_rows = list(reply_response.data or [])
    if not reply_rows:
        raise OutreachReplySendStoreError("Reply conversation was not found.")
    reply = dict(reply_rows[0])

    existing_response = (
        active_client.table(REPLY_SEND_TABLE)
        .select("*")
        .eq("reply_id", cleaned_reply_id)
        .limit(1)
        .execute()
    )
    existing_rows = list(existing_response.data or [])
    if existing_rows:
        existing = dict(existing_rows[0])
        status = _safe_text(existing.get("status")).lower()
        if status in {"queued", "processing"}:
            raise OutreachReplySendStoreError(
                f"This reply job is already {status} and cannot be edited."
            )
        response = (
            active_client.table(REPLY_SEND_TABLE)
            .update(
                {
                    "sent_target_id": reply.get("sent_target_id"),
                    "assigned_account_id": reply.get("assigned_account_id"),
                    "user_name": reply.get("user_name"),
                    "linkedin_url": reply.get("linkedin_url"),
                    "message_text": cleaned_message,
                    "status": "prepared",
                    "prepared_at": _utc_now(),
                    "queued_at": None,
                    "started_at": None,
                    "sent_at": None,
                    "failed_at": None,
                    "last_error": None,
                    "updated_at": _utc_now(),
                }
            )
            .eq("id", existing.get("id"))
            .execute()
        )
    else:
        response = (
            active_client.table(REPLY_SEND_TABLE)
            .insert(
                {
                    "reply_id": cleaned_reply_id,
                    "sent_target_id": reply.get("sent_target_id"),
                    "assigned_account_id": reply.get("assigned_account_id"),
                    "user_name": reply.get("user_name"),
                    "linkedin_url": reply.get("linkedin_url"),
                    "message_text": cleaned_message,
                    "status": "prepared",
                    "prepared_at": _utc_now(),
                }
            )
            .execute()
        )

    rows = list(response.data or [])
    if not rows:
        raise OutreachReplySendStoreError("Could not prepare the reply message.")
    return dict(rows[0])


def queue_prepared_reply_send(
    *,
    reply_id: str,
    client: Client | None = None,
) -> dict:
    cleaned_reply_id = _safe_text(reply_id)
    if not cleaned_reply_id:
        raise OutreachReplySendStoreError("reply_id is required.")

    active_client = client or get_outreach_client()
    response = (
        active_client.table(REPLY_SEND_TABLE)
        .update(
            {
                "status": "queued",
                "queued_at": _utc_now(),
                "last_error": None,
                "updated_at": _utc_now(),
            }
        )
        .eq("reply_id", cleaned_reply_id)
        .eq("status", "prepared")
        .execute()
    )
    rows = list(response.data or [])
    if not rows:
        raise OutreachReplySendStoreError(
            "Only a prepared reply message can be queued."
        )
    return dict(rows[0])


def prepare_and_queue_reply_send(
    *,
    reply_id: str,
    message_text: str,
    client: Client | None = None,
) -> dict:
    """Save the exact customized text and immediately make it worker-ready."""

    active_client = client or get_outreach_client()
    prepare_reply_send(
        reply_id=reply_id,
        message_text=message_text,
        client=active_client,
    )
    return queue_prepared_reply_send(
        reply_id=reply_id,
        client=active_client,
    )


def load_queued_reply_sends(
    *,
    account_id: str,
    client: Client,
) -> list[dict]:
    response = (
        client.table(REPLY_SEND_TABLE)
        .select("*")
        .eq("assigned_account_id", _safe_text(account_id))
        .eq("status", "queued")
        .order("queued_at", desc=False)
        .execute()
    )
    return [dict(row) for row in list(response.data or [])]


def claim_reply_send(*, job_id: str, client: Client) -> dict:
    response = (
        client.table(REPLY_SEND_TABLE)
        .update(
            {
                "status": "processing",
                "started_at": _utc_now(),
                "send_attempt_count": 1,
                "last_error": None,
                "updated_at": _utc_now(),
            }
        )
        .eq("id", _safe_text(job_id))
        .eq("status", "queued")
        .execute()
    )
    rows = list(response.data or [])
    if not rows:
        raise OutreachReplySendStoreError("Reply send job could not be claimed.")
    return dict(rows[0])


def finish_reply_send(
    *,
    job_id: str,
    sent: bool,
    error_message: str = "",
    client: Client,
) -> dict:
    now = _utc_now()
    values = {
        "status": "sent" if sent else "failed",
        "sent_at": now if sent else None,
        "failed_at": None if sent else now,
        "last_error": None if sent else _safe_text(error_message)[:4000],
        "updated_at": now,
    }
    response = (
        client.table(REPLY_SEND_TABLE)
        .update(values)
        .eq("id", _safe_text(job_id))
        .eq("status", "processing")
        .execute()
    )
    rows = list(response.data or [])
    return dict(rows[0]) if rows else values
