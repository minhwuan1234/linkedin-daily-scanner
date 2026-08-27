from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

from app.outreach_account_pool import (
    OUTREACH_ACCOUNT_DISPLAY_NAMES,
    OutreachAccountPool,
)
from app.settings import load_settings


SESSION_TABLE = "outreach_account_sessions"

SESSION_STATUSES = {
    "never_checked",
    "pending",
    "checking",
    "logged_in",
    "logged_out",
    "checkpoint",
    "busy",
    "unknown",
    "failed",
}


class OutreachSessionStatusError(RuntimeError):
    pass


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def get_outreach_supabase_client() -> Client:
    settings = load_settings()

    if not settings.outreach_supabase_url:
        raise OutreachSessionStatusError(
            "Missing OUTREACH_SUPABASE_URL."
        )

    if not settings.outreach_supabase_secret_key:
        raise OutreachSessionStatusError(
            "Missing OUTREACH_SUPABASE_SECRET_KEY."
        )

    return create_client(
        settings.outreach_supabase_url,
        settings.outreach_supabase_secret_key,
    )


def _account_rows_from_pool() -> list[dict[str, Any]]:
    pool = OutreachAccountPool()

    return [
        {
            "account_id": account.account_id,
            "display_name": account.display_name,
        }
        for account in pool.accounts
    ]


def ensure_session_rows(
    *,
    client: Client | None = None,
) -> list[dict[str, Any]]:
    active_client = client or get_outreach_supabase_client()
    accounts = _account_rows_from_pool()

    existing_response = (
        active_client
        .table(SESSION_TABLE)
        .select("account_id")
        .execute()
    )

    existing_ids = {
        _safe_text(row.get("account_id"))
        for row in list(existing_response.data or [])
    }

    missing = [
        {
            "account_id": account["account_id"],
            "display_name": account["display_name"],
            "status": "never_checked",
            "updated_at": _utc_now_iso(),
        }
        for account in accounts
        if account["account_id"] not in existing_ids
    ]

    if missing:
        (
            active_client
            .table(SESSION_TABLE)
            .insert(missing)
            .execute()
        )

    return accounts


def list_outreach_session_statuses(
    *,
    client: Client | None = None,
) -> list[dict[str, Any]]:
    active_client = client or get_outreach_supabase_client()
    accounts = ensure_session_rows(client=active_client)

    response = (
        active_client
        .table(SESSION_TABLE)
        .select(
            "account_id,display_name,status,requested_at,"
            "checking_at,checked_at,current_url,last_error,updated_at"
        )
        .execute()
    )

    rows_by_id = {
        _safe_text(row.get("account_id")): dict(row)
        for row in list(response.data or [])
    }

    result: list[dict[str, Any]] = []

    for account in accounts:
        account_id = account["account_id"]
        row = rows_by_id.get(account_id, {})
        status = _safe_text(row.get("status")) or "never_checked"

        if status not in SESSION_STATUSES:
            status = "unknown"

        result.append(
            {
                "account_id": account_id,
                "display_name": (
                    _safe_text(row.get("display_name"))
                    or account["display_name"]
                    or OUTREACH_ACCOUNT_DISPLAY_NAMES.get(account_id, account_id)
                ),
                "status": status,
                "requested_at": row.get("requested_at"),
                "checking_at": row.get("checking_at"),
                "checked_at": row.get("checked_at"),
                "current_url": row.get("current_url"),
                "last_error": row.get("last_error"),
                "updated_at": row.get("updated_at"),
            }
        )

    return result


def queue_outreach_session_checks(
    *,
    account_ids: list[str] | None = None,
    client: Client | None = None,
) -> list[dict[str, Any]]:
    active_client = client or get_outreach_supabase_client()
    accounts = ensure_session_rows(client=active_client)
    allowed_ids = {item["account_id"] for item in accounts}

    requested_ids = (
        [str(value or "").strip() for value in account_ids]
        if account_ids is not None
        else [item["account_id"] for item in accounts]
    )

    cleaned_ids: list[str] = []
    seen: set[str] = set()

    for account_id in requested_ids:
        if not account_id or account_id in seen:
            continue
        if account_id not in allowed_ids:
            raise OutreachSessionStatusError(
                f"Unknown Outreach account: {account_id}"
            )
        seen.add(account_id)
        cleaned_ids.append(account_id)

    if not cleaned_ids:
        raise OutreachSessionStatusError(
            "No Outreach accounts selected for session check."
        )

    now = _utc_now_iso()

    for account_id in cleaned_ids:
        display_name = OUTREACH_ACCOUNT_DISPLAY_NAMES.get(
            account_id,
            account_id,
        )

        (
            active_client
            .table(SESSION_TABLE)
            .upsert(
                {
                    "account_id": account_id,
                    "display_name": display_name,
                    "status": "pending",
                    "requested_at": now,
                    "checking_at": None,
                    "last_error": None,
                    "updated_at": now,
                },
                on_conflict="account_id",
            )
            .execute()
        )

    return list_outreach_session_statuses(client=active_client)
