from __future__ import annotations

import argparse
import asyncio
import logging
import os
import time
from typing import Any

from supabase import AsyncClient, acreate_client

from app.linkedin_message_sender import send_message_once
from app.linkedin_profile_message import get_profile_name
from app.outreach_account_pool import OutreachAccountPool
from app.outreach_message_executor import get_outreach_supabase_client
from app.outreach_reply_send_store import (
    claim_reply_send,
    finish_reply_send,
    load_queued_reply_sends,
)
from app.settings import load_settings


DEFAULT_ACCOUNT_ID = "outreach_account_01"
BETWEEN_SENDS_SECONDS = 2.5
REPLY_SEND_TABLE = "outreach_reply_send_jobs"

logger = logging.getLogger("outreach_reply_send_worker")

_realtime_queue: asyncio.Queue[bool] | None = None
_realtime_account_id = ""


def run_once(account_id: str, *, quiet_empty: bool = False) -> dict[str, int]:
    """Send every queued reply for exactly one Outreach account, then exit."""

    pool = OutreachAccountPool()
    account = pool.get_account(account_id)
    client = get_outreach_supabase_client()
    jobs = load_queued_reply_sends(
        account_id=account.account_id,
        client=client,
    )

    if not jobs:
        if not quiet_empty:
            print("No queued reply messages for this account.")
        return {"sent": 0, "failed": 0}

    logger.info(
        "Reply send worker | account=%s | queued_jobs=%d",
        account.account_id,
        len(jobs),
    )

    browser = account.create_browser_manager()
    sent_count = 0
    failed_count = 0

    try:
        browser.start()

        for queued_job in jobs:
            job_id = str(queued_job.get("id") or "").strip()
            user_name = str(queued_job.get("user_name") or "").strip()

            try:
                job = claim_reply_send(job_id=job_id, client=client)
                linkedin_url = str(job.get("linkedin_url") or "").strip()
                message_text = str(job.get("message_text") or "").strip()
                if not linkedin_url or not message_text:
                    raise RuntimeError(
                        "Queued reply requires linkedin_url and message_text."
                    )

                logger.info(
                    "Opening reply target | job_id=%s | user=%s | url=%s",
                    job_id,
                    user_name,
                    linkedin_url,
                )
                page = browser.open_linkedin_url(linkedin_url)
                profile_name = get_profile_name(page)
                expected_name = str(
                    profile_name.get("full_name") or user_name
                ).strip()

                result = send_message_once(
                    page,
                    message_text,
                    expected_profile_name=expected_name,
                )
                if not bool(result.get("sent_verified")):
                    raise RuntimeError("LinkedIn message send was not verified.")

                finish_reply_send(
                    job_id=job_id,
                    sent=True,
                    client=client,
                )
                sent_count += 1
                logger.info(
                    "REPLY SENT | job_id=%s | user=%s | text_length=%d",
                    job_id,
                    expected_name,
                    len(message_text),
                )

            except Exception as exc:
                failed_count += 1
                logger.exception(
                    "REPLY SEND FAILED | job_id=%s | user=%s | error=%s",
                    job_id,
                    user_name,
                    exc,
                )
                try:
                    finish_reply_send(
                        job_id=job_id,
                        sent=False,
                        error_message=f"{type(exc).__name__}: {exc}",
                        client=client,
                    )
                except Exception:
                    logger.exception(
                        "Could not mark reply send job failed | job_id=%s",
                        job_id,
                    )

            time.sleep(BETWEEN_SENDS_SECONDS)

    finally:
        browser.stop()

    print("")
    print("Reply send worker completed.")
    print(f"Account: {account.account_id}")
    print(f"Sent: {sent_count}")
    print(f"Failed: {failed_count}")
    print("Browser closed.")
    return {"sent": sent_count, "failed": failed_count}


def _payload_record(payload: Any) -> dict:
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


def _enqueue_realtime_work() -> None:
    if _realtime_queue is not None and _realtime_queue.empty():
        _realtime_queue.put_nowait(True)


def _handle_realtime_change(payload: Any) -> None:
    row = _payload_record(payload)
    if (
        str(row.get("status") or "").strip().lower() == "queued"
        and str(row.get("assigned_account_id") or "").strip()
        == _realtime_account_id
    ):
        logger.info(
            "Realtime queued reply received | account=%s | job_id=%s",
            _realtime_account_id,
            row.get("id"),
        )
        _enqueue_realtime_work()


async def _get_async_client() -> AsyncClient:
    settings = load_settings()
    return await acreate_client(
        settings.outreach_supabase_url,
        settings.outreach_supabase_secret_key,
    )


async def _recover_queued_jobs(client: AsyncClient, account_id: str) -> None:
    """One reconciliation read at startup/reconnect; this is not polling."""

    response = await (
        client.table(REPLY_SEND_TABLE)
        .select("id")
        .eq("assigned_account_id", account_id)
        .eq("status", "queued")
        .limit(1)
        .execute()
    )
    if list(response.data or []):
        _enqueue_realtime_work()


def _build_subscribe_callback(account_id: str):
    def on_subscribe(status: Any, error: Any = None) -> None:
        status_text = str(getattr(status, "value", status) or "").lower()
        if "subscribed" in status_text:
            logger.info(
                "Supabase Realtime connected | account=%s | no polling",
                account_id,
            )
            # Reconcile once after every (re)subscription. The queued worker
            # pass performs one read and then blocks again; there is no timer.
            _enqueue_realtime_work()
        elif error:
            logger.warning("Realtime status=%s | error=%s", status, error)

    return on_subscribe


async def run_realtime(account_id: str) -> None:
    """Wait for queued-row events without issuing repeated HTTP requests."""

    global _realtime_queue, _realtime_account_id
    _realtime_queue = asyncio.Queue(maxsize=1)
    _realtime_account_id = account_id
    client = await _get_async_client()
    channel = (
        client.channel(f"outreach-reply-send-{account_id}")
        .on_postgres_changes(
            "*",
            schema="public",
            table=REPLY_SEND_TABLE,
            callback=_handle_realtime_change,
        )
    )

    try:
        await channel.subscribe(_build_subscribe_callback(account_id))
        await _recover_queued_jobs(client, account_id)
        while True:
            await _realtime_queue.get()
            try:
                await asyncio.to_thread(
                    run_once,
                    account_id,
                    quiet_empty=True,
                )
            except Exception:
                logger.exception(
                    "Realtime reply send failed | account=%s",
                    account_id,
                )
            finally:
                _realtime_queue.task_done()
    finally:
        try:
            await client.remove_channel(channel)
        except Exception:
            pass


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send queued LinkedIn replies for one Outreach account."
    )
    parser.add_argument(
        "--account-id",
        default=os.getenv("OUTREACH_REPLY_SEND_ACCOUNT_ID", DEFAULT_ACCOUNT_ID),
        help=f"Outreach account browser profile (default: {DEFAULT_ACCOUNT_ID}).",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process the current queue once and exit instead of staying active.",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    args = _parse_args()
    account_id = str(args.account_id).strip()
    try:
        if args.once:
            run_once(account_id)
        else:
            asyncio.run(run_realtime(account_id))
    except KeyboardInterrupt:
        logger.info("Reply send worker stopped | account=%s", account_id)


if __name__ == "__main__":
    main()
