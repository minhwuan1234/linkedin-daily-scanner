from __future__ import annotations

import logging
from datetime import datetime, timezone
from queue import Queue
from threading import Lock
from typing import Any

from app.linkedin_session_checker import (
    check_outreach_account_session,
)
from app.outreach_account_pool import OutreachAccountPool
from app.outreach_session_status import (
    SESSION_TABLE,
    get_outreach_supabase_client,
)


logger = logging.getLogger("outreach_session_worker")

# Realtime callbacks stay lightweight. They only enqueue account IDs.
_work_queue: Queue[str] = Queue()
_queued_accounts: set[str] = set()
_queue_lock = Lock()

_RECOVER_PENDING = "__recover_pending__"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _payload_record(payload: Any) -> dict[str, Any]:
    """
    Accept the common realtime-py / Supabase Postgres Changes payload shapes.

    We intentionally keep this tolerant because realtime-py has changed the
    outer envelope across versions while the row itself remains the same.
    """

    if not isinstance(payload, dict):
        return {}

    for key in ("new", "record"):
        value = payload.get(key)
        if isinstance(value, dict):
            return dict(value)

    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("record", "new"):
            value = data.get(key)
            if isinstance(value, dict):
                return dict(value)

    return {}


def _enqueue_account(account_id: str) -> None:
    account_id = _clean(account_id)

    if not account_id:
        return

    with _queue_lock:
        if account_id in _queued_accounts:
            return

        _queued_accounts.add(account_id)

    _work_queue.put(account_id)


def _finish_account(account_id: str) -> None:
    with _queue_lock:
        _queued_accounts.discard(account_id)


def _enqueue_recovery() -> None:
    _work_queue.put(_RECOVER_PENDING)


def _handle_realtime_change(payload: Any) -> None:
    """
    Realtime event callback.

    Only pending rows are interesting. Updates produced by the worker itself
    (checking/logged_in/logged_out/etc.) are ignored.
    """

    row = _payload_record(payload)

    if _clean(row.get("status")).lower() != "pending":
        return

    _enqueue_account(
        _clean(row.get("account_id"))
    )


def _handle_subscribe_status(status: Any, error: Any = None) -> None:
    """
    When the websocket becomes subscribed (including reconnects), perform one
    tiny reconciliation query. This protects against a request being created
    while the Mac was offline without returning to continuous polling.
    """

    status_text = _clean(
        getattr(status, "value", status)
    ).lower()

    if "subscribed" in status_text:
        logger.info("Supabase Realtime connected.")
        _enqueue_recovery()
        return

    if error:
        logger.warning(
            "Supabase Realtime status=%s error=%s",
            status,
            error,
        )


def recover_pending_requests(client) -> None:
    """
    One read at startup/reconnect only — NOT a timer.

    This is the only GET used by the worker while idle.
    """

    response = (
        client
        .table(SESSION_TABLE)
        .select("account_id")
        .eq("status", "pending")
        .order("requested_at", desc=False)
        .execute()
    )

    for row in list(response.data or []):
        _enqueue_account(
            _clean(row.get("account_id"))
        )


def claim_session_check(
    client,
    *,
    account_id: str,
) -> bool:
    """
    Atomic-enough claim for this small worker pool:
    update only when the row is still pending.

    If another worker already claimed it, Supabase returns no updated row.
    """

    now = _utc_now_iso()

    response = (
        client
        .table(SESSION_TABLE)
        .update(
            {
                "status": "checking",
                "checking_at": now,
                "last_error": None,
                "updated_at": now,
            }
        )
        .eq("account_id", account_id)
        .eq("status", "pending")
        .execute()
    )

    return bool(list(response.data or []))


def complete_session_check(
    client,
    *,
    account_id: str,
    status: str,
    current_url: str | None,
    detail: str | None,
) -> None:
    now = _utc_now_iso()

    (
        client
        .table(SESSION_TABLE)
        .update(
            {
                "status": status,
                "checked_at": now,
                "current_url": current_url,
                "last_error": (
                    detail
                    if status in {
                        "unknown",
                        "failed",
                        "busy",
                        "checkpoint",
                    }
                    else None
                ),
                "updated_at": now,
            }
        )
        .eq("account_id", account_id)
        .execute()
    )


def fail_session_check(
    client,
    *,
    account_id: str,
    error: Exception,
) -> None:
    now = _utc_now_iso()

    (
        client
        .table(SESSION_TABLE)
        .update(
            {
                "status": "failed",
                "checked_at": now,
                "last_error": str(error)[:2000],
                "updated_at": now,
            }
        )
        .eq("account_id", account_id)
        .execute()
    )


def process_account(
    client,
    pool: OutreachAccountPool,
    account_id: str,
) -> None:
    if not claim_session_check(
        client,
        account_id=account_id,
    ):
        return

    account = pool.get_account(
        account_id
    )

    logger.info(
        "Checking LinkedIn session: %s",
        account_id,
    )

    try:
        result = check_outreach_account_session(
            account
        )

        complete_session_check(
            client,
            account_id=account_id,
            status=result.status,
            current_url=result.current_url,
            detail=result.detail,
        )

        logger.info(
            "Session check complete | account=%s | status=%s",
            account_id,
            result.status,
        )

    except Exception as exc:
        logger.exception(
            "Session check failed | account=%s",
            account_id,
        )

        fail_session_check(
            client,
            account_id=account_id,
            error=exc,
        )


def run_forever() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    # Do not print every successful HTTP request.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    client = get_outreach_supabase_client()
    pool = OutreachAccountPool()

    logger.info(
        "Outreach Session Worker started — Realtime mode, no polling."
    )

    channel = (
        client
        .channel("outreach-session-worker")
        .on_postgres_changes(
            "*",
            schema="public",
            table=SESSION_TABLE,
            callback=_handle_realtime_change,
        )
    )

    try:
        channel.subscribe(
            _handle_subscribe_status
        )

        # Safety reconciliation for the initial startup.
        # The queue de-duplicates this if the subscribe callback also fires.
        _enqueue_recovery()

        while True:
            item = _work_queue.get()

            try:
                if item == _RECOVER_PENDING:
                    recover_pending_requests(
                        client
                    )
                    continue

                process_account(
                    client,
                    pool,
                    item,
                )

            finally:
                if item != _RECOVER_PENDING:
                    _finish_account(
                        item
                    )

                _work_queue.task_done()

    except KeyboardInterrupt:
        logger.info(
            "Outreach Session Worker stopped."
        )

    finally:
        try:
            client.remove_channel(
                channel
            )
        except Exception:
            pass


if __name__ == "__main__":
    run_forever()
