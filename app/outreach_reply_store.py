from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from supabase import Client

from app.outreach_dashboard_store import get_outreach_client


REPLY_TABLE = "outreach_reply_messages"


class OutreachReplyStoreError(RuntimeError):
    pass


def _safe_text(value) -> str:
    return str(value or "").strip()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _message_fingerprint(
    *,
    sent_target_id: str,
    message_text: str,
    linkedin_message_time: str,
) -> str:
    source = "\n".join(
        (
            _safe_text(sent_target_id),
            " ".join(_safe_text(message_text).split()),
            _safe_text(linkedin_message_time),
        )
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def save_outreach_reply(
    *,
    sent_target_id: str,
    prospect_id: str,
    assigned_account_id: str,
    user_name: str,
    linkedin_url: str,
    message_text: str,
    linkedin_message_time: str = "",
    match_reason: str = "",
    match_similarity: float = 0.0,
    client: Client | None = None,
) -> dict:
    """Persist one verified reply without duplicating repeat scans."""

    cleaned_target_id = _safe_text(sent_target_id)
    cleaned_name = _safe_text(user_name)
    cleaned_url = _safe_text(linkedin_url)
    cleaned_message = " ".join(_safe_text(message_text).split())
    cleaned_message_time = _safe_text(linkedin_message_time)

    if not cleaned_target_id:
        raise OutreachReplyStoreError("sent_target_id is required.")
    if not cleaned_name:
        raise OutreachReplyStoreError("user_name is required.")
    if not cleaned_url:
        raise OutreachReplyStoreError("linkedin_url is required.")
    if not cleaned_message:
        raise OutreachReplyStoreError("message_text is required.")

    active_client = client or get_outreach_client()
    fingerprint = _message_fingerprint(
        sent_target_id=cleaned_target_id,
        message_text=cleaned_message,
        linkedin_message_time=cleaned_message_time,
    )

    existing_response = (
        active_client.table(REPLY_TABLE)
        .select("*")
        .eq("message_fingerprint", fingerprint)
        .limit(1)
        .execute()
    )
    existing_rows = list(existing_response.data or [])
    if existing_rows:
        return dict(existing_rows[0])

    payload = {
        "sent_target_id": cleaned_target_id,
        "prospect_id": _safe_text(prospect_id) or None,
        "assigned_account_id": _safe_text(assigned_account_id),
        "user_name": cleaned_name,
        "linkedin_url": cleaned_url,
        "message_text": cleaned_message,
        "linkedin_message_time": cleaned_message_time or None,
        "match_reason": _safe_text(match_reason) or None,
        "match_similarity": max(0.0, min(1.0, float(match_similarity or 0.0))),
        "message_fingerprint": fingerprint,
        "captured_at": _utc_now(),
    }

    response = active_client.table(REPLY_TABLE).insert(payload).execute()
    rows = list(response.data or [])
    return dict(rows[0]) if rows else payload


def list_recent_outreach_replies(
    *,
    limit: int = 5,
    client: Client | None = None,
) -> list[dict]:
    """Return the newest reply for each of up to ``limit`` people."""

    safe_limit = max(1, min(int(limit or 5), 25))
    active_client = client or get_outreach_client()
    response = (
        active_client.table(REPLY_TABLE)
        .select(
            (
                "id,sent_target_id,prospect_id,assigned_account_id,"
                "user_name,linkedin_url,message_text,linkedin_message_time,"
                "match_reason,match_similarity,captured_at"
            )
        )
        .order("captured_at", desc=True)
        .limit(max(50, safe_limit * 10))
        .execute()
    )

    replies: list[dict] = []
    seen_people: set[str] = set()

    for raw_row in list(response.data or []):
        row = dict(raw_row)
        identity = _safe_text(row.get("linkedin_url")).casefold()
        if not identity:
            identity = "|".join(
                (
                    _safe_text(row.get("assigned_account_id")).casefold(),
                    _safe_text(row.get("user_name")).casefold(),
                )
            )

        if identity in seen_people:
            continue

        seen_people.add(identity)
        replies.append(row)

        if len(replies) >= safe_limit:
            break

    return replies
