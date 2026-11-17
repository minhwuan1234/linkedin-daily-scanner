from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.postgres_client import AsyncClient, acreate_client

from app.linkedin_session_checker import (
    check_outreach_account_session,
)
from app.outreach_account_pool import OutreachAccountPool
from app.outreach_session_status import SESSION_TABLE
from app.settings import load_settings


logger = logging.getLogger("outreach_session_worker")

_work_queue: asyncio.Queue[str] | None = None
_queued_accounts: set[str] = set()

_RECOVER_PENDING = "__recover_pending__"


def _get_work_queue() -> asyncio.Queue[str]:
    """
    Return the queue created inside the currently running asyncio loop.

    Python 3.9 can bind asyncio primitives to the event loop that existed
    when they were created. Creating the queue at module import time can
    therefore produce "Future attached to a different loop" once
    asyncio.run() starts its own loop.
    """

    if _work_queue is None:
        raise RuntimeError(
            "Session worker queue has not been initialized."
        )

    return _work_queue


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(value: Any) -> str:
    return str(value or "").strip()




async def get_async_supabase_client() -> AsyncClient:
    return await acreate_client()



def _enqueue_account(
    account_id: str,
) -> None:
    account_id = _clean(account_id)

    if (
        not account_id
        or account_id in _queued_accounts
    ):
        return

    _queued_accounts.add(
        account_id
    )

    _get_work_queue().put_nowait(
        account_id
    )


def _finish_account(
    account_id: str,
) -> None:
    _queued_accounts.discard(
        account_id
    )


def _enqueue_recovery() -> None:
    _get_work_queue().put_nowait(
        _RECOVER_PENDING
    )






async def recover_pending_requests(
    client: AsyncClient,
) -> None:
    """
    One tiny GET at startup/reconnect only.
    No polling loop.
    """

    response = await (
        client
        .table(SESSION_TABLE)
        .select("account_id")
        .eq("status", "pending")
        .order(
            "requested_at",
            desc=False,
        )
        .execute()
    )

    for row in list(
        response.data
        or []
    ):
        _enqueue_account(
            _clean(
                row.get("account_id")
            )
        )


async def claim_session_check(
    client: AsyncClient,
    *,
    account_id: str,
) -> bool:
    now = _utc_now_iso()

    response = await (
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
        .eq(
            "account_id",
            account_id,
        )
        .eq(
            "status",
            "pending",
        )
        .execute()
    )

    return bool(
        list(
            response.data
            or []
        )
    )


async def complete_session_check(
    client: AsyncClient,
    *,
    account_id: str,
    status: str,
    current_url: str | None,
    detail: str | None,
) -> None:
    now = _utc_now_iso()

    await (
        client
        .table(SESSION_TABLE)
        .update(
            {
                "status": status,
                "checked_at": now,
                "current_url": current_url,
                "last_error": (
                    detail
                    if status
                    in {
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
        .eq(
            "account_id",
            account_id,
        )
        .execute()
    )


async def fail_session_check(
    client: AsyncClient,
    *,
    account_id: str,
    error: Exception,
) -> None:
    now = _utc_now_iso()

    await (
        client
        .table(SESSION_TABLE)
        .update(
            {
                "status": "failed",
                "checked_at": now,
                "last_error": (
                    str(error)[:2000]
                ),
                "updated_at": now,
            }
        )
        .eq(
            "account_id",
            account_id,
        )
        .execute()
    )


async def process_account(
    client: AsyncClient,
    pool: OutreachAccountPool,
    account_id: str,
) -> None:
    claimed = await claim_session_check(
        client,
        account_id=account_id,
    )

    if not claimed:
        return

    try:
        try:
            account = pool.get_account(account_id)
        except KeyError as exc:
            raise RuntimeError(
                f"{account_id} is not in this worker's configured accounts. "
                "Pull the latest code, check OUTREACH_ACCOUNT_IDS in .env "
                "or the shell environment, then restart the worker."
            ) from exc

        if not getattr(account, "enabled", True):
            raise RuntimeError(f"Outreach account is paused: {account_id}")
        logger.info("Checking LinkedIn session: %s", account_id)
        # Playwright/browser manager in this repo is synchronous.
        # Run it off the asyncio event loop so the Realtime websocket stays
        # alive while Chromium is being checked.
        result = await asyncio.to_thread(
            check_outreach_account_session,
            account,
        )

        await complete_session_check(
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

        await fail_session_check(
            client,
            account_id=account_id,
            error=exc,
        )


async def worker_loop(client: AsyncClient, pool: OutreachAccountPool) -> None:
    queue = _get_work_queue()
    while True:
        try:
            item = await asyncio.wait_for(queue.get(), timeout=5)
        except asyncio.TimeoutError:
            try:
                await recover_pending_requests(client)
            except Exception:
                logger.exception("Session worker could not load pending requests")
            continue
        try:
            if item == _RECOVER_PENDING:
                await recover_pending_requests(client)
            else:
                await process_account(client, pool, item)
        except Exception:
            logger.exception("Session worker request failed | account=%s", item)
        finally:
            if item != _RECOVER_PENDING:
                _finish_account(item)
            queue.task_done()



async def run_forever() -> None:
    global _work_queue
    _work_queue = asyncio.Queue()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    client = await get_async_supabase_client()
    pool = OutreachAccountPool()
    logger.info("Outreach Session Worker started — PostgreSQL polling every 5 seconds")
    _enqueue_recovery()
    await worker_loop(client, pool)



def main() -> None:
    try:
        asyncio.run(
            run_forever()
        )
    except KeyboardInterrupt:
        logger.info(
            "Outreach Session Worker stopped."
        )


if __name__ == "__main__":
    main()
