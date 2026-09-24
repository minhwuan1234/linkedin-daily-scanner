from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from supabase import Client

from app.outreach_account_pool import (
    DEFAULT_OUTREACH_ACCOUNT_IDS,
    OUTREACH_ACCOUNT_DISPLAY_NAMES,
)
from app.outreach_dashboard_store import get_outreach_client


REPLY_TABLE = "outreach_reply_messages"
MESSAGE_TARGET_TABLE = "outreach_message_targets"
MESSAGE_BATCH_TABLE = "outreach_message_batches"


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
    conversation_messages: list[dict] | None = None,
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
        .eq("sent_target_id", cleaned_target_id)
        .order("captured_at", desc=True)
        .limit(1)
        .execute()
    )
    existing_rows = list(existing_response.data or [])
    if existing_rows:
        existing = dict(existing_rows[0])
        updates = {
            "prospect_id": _safe_text(prospect_id) or None,
            "assigned_account_id": _safe_text(assigned_account_id),
            "user_name": cleaned_name,
            "linkedin_url": cleaned_url,
            "message_text": cleaned_message,
            "linkedin_message_time": cleaned_message_time or None,
            "conversation_messages": list(conversation_messages or []),
            "match_reason": _safe_text(match_reason) or None,
            "match_similarity": max(
                0.0,
                min(1.0, float(match_similarity or 0.0)),
            ),
            "message_fingerprint": fingerprint,
            "captured_at": _utc_now(),
        }
        update_response = (
            active_client.table(REPLY_TABLE)
            .update(updates)
            .eq("id", existing.get("id"))
            .execute()
        )
        updated_rows = list(update_response.data or [])
        if updated_rows:
            return dict(updated_rows[0])
        existing.update(updates)
        return existing

    payload = {
        "sent_target_id": cleaned_target_id,
        "prospect_id": _safe_text(prospect_id) or None,
        "assigned_account_id": _safe_text(assigned_account_id),
        "user_name": cleaned_name,
        "linkedin_url": cleaned_url,
        "message_text": cleaned_message,
        "linkedin_message_time": cleaned_message_time or None,
        "conversation_messages": list(conversation_messages or []),
        "match_reason": _safe_text(match_reason) or None,
        "match_similarity": max(0.0, min(1.0, float(match_similarity or 0.0))),
        "message_fingerprint": fingerprint,
        "captured_at": _utc_now(),
    }

    response = active_client.table(REPLY_TABLE).insert(payload).execute()
    rows = list(response.data or [])
    return dict(rows[0]) if rows else payload


REPLY_SELECT_FIELDS = (
    "id,sent_target_id,prospect_id,assigned_account_id,"
    "user_name,linkedin_url,message_text,linkedin_message_time,"
    "conversation_messages,match_reason,match_similarity,captured_at"
)


def _attach_batch_codes(replies: list[dict], active_client: Client) -> None:
    """Add the source message batch to reply records in place."""
    target_ids = [
        _safe_text(reply.get("sent_target_id"))
        for reply in replies
        if _safe_text(reply.get("sent_target_id"))
    ]
    target_to_batch: dict[str, str] = {}
    batch_codes: dict[str, str] = {}

    if target_ids:
        target_response = (
            active_client.table(MESSAGE_TARGET_TABLE)
            .select("id,batch_id")
            .in_("id", target_ids)
            .execute()
        )
        for target in list(target_response.data or []):
            target_id = _safe_text(target.get("id"))
            batch_id = _safe_text(target.get("batch_id"))
            if target_id and batch_id:
                target_to_batch[target_id] = batch_id

        unique_batch_ids = list(dict.fromkeys(target_to_batch.values()))
        if unique_batch_ids:
            batch_response = (
                active_client.table(MESSAGE_BATCH_TABLE)
                .select("id,batch_code")
                .in_("id", unique_batch_ids)
                .execute()
            )
            for batch in list(batch_response.data or []):
                batch_id = _safe_text(batch.get("id"))
                batch_code = _safe_text(batch.get("batch_code"))
                if batch_id and batch_code:
                    batch_codes[batch_id] = batch_code

    for reply in replies:
        batch_id = target_to_batch.get(_safe_text(reply.get("sent_target_id")), "")
        reply["message_batch_code"] = batch_codes.get(batch_id) or None


def list_outreach_reply_page(
    *,
    account_id: str,
    offset: int = 0,
    limit: int = 20,
    client: Client | None = None,
) -> dict:
    """Fetch a stable page of raw reply rows for one account."""
    cleaned_account_id = _safe_text(account_id)
    if cleaned_account_id not in DEFAULT_OUTREACH_ACCOUNT_IDS[:5]:
        raise OutreachReplyStoreError("Unknown Outreach account.")
    safe_offset = max(0, int(offset))
    safe_limit = max(1, min(int(limit), 50))
    active_client = client or get_outreach_client()
    response = (
        active_client.table(REPLY_TABLE)
        .select(REPLY_SELECT_FIELDS)
        .eq("assigned_account_id", cleaned_account_id)
        .order("captured_at", desc=True)
        .order("id", desc=True)
        .range(safe_offset, safe_offset + safe_limit)
        .execute()
    )
    fetched = [dict(row) for row in list(response.data or [])]
    replies = fetched[:safe_limit]
    _attach_batch_codes(replies, active_client)
    return {
        "replies": replies,
        "next_offset": safe_offset + len(replies),
        "has_more": len(fetched) > safe_limit,
    }


def list_recent_outreach_replies(
    *,
    limit: int = 50,
    client: Client | None = None,
) -> list[dict]:
    """Return the newest reply for each of up to ``limit`` people."""

    safe_limit = max(1, min(int(limit or 50), 100))
    active_client = client or get_outreach_client()
    response = (
        active_client.table(REPLY_TABLE)
        .select(REPLY_SELECT_FIELDS)
        .order("captured_at", desc=True)
        .limit(max(50, safe_limit * 10))
        .execute()
    )

    replies: list[dict] = []
    seen_people: set[str] = set()

    for raw_row in list(response.data or []):
        row = dict(raw_row)
        account_identity = _safe_text(
            row.get("assigned_account_id")
        ).casefold()
        person_identity = _safe_text(row.get("linkedin_url")).casefold()
        if person_identity:
            identity = "|".join((account_identity, person_identity))
        else:
            identity = "|".join(
                (
                    account_identity,
                    _safe_text(row.get("user_name")).casefold(),
                )
            )

        if identity in seen_people:
            continue

        seen_people.add(identity)
        replies.append(row)

        if len(replies) >= safe_limit:
            break

    _attach_batch_codes(replies, active_client)
    return replies


def list_outreach_reply_accounts(
    *,
    client: Client | None = None,
    include_counts: bool = False,
) -> list[dict]:
    """Return up to five Outreach accounts with their display names."""

    accounts = [
        {
            "account_id": account_id,
            "display_name": OUTREACH_ACCOUNT_DISPLAY_NAMES.get(
                account_id,
                account_id,
            ),
        }
        for account_id in DEFAULT_OUTREACH_ACCOUNT_IDS[:5]
    ]
    if include_counts:
        active_client = client or get_outreach_client()
        for account in accounts:
            response = (
                active_client.table(REPLY_TABLE)
                .select("id", count="exact", head=True)
                .eq("assigned_account_id", account["account_id"])
                .execute()
            )
            account["reply_count"] = int(response.count or 0)
    return accounts
