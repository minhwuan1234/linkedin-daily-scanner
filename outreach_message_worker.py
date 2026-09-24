from __future__ import annotations

import asyncio
import logging
from typing import Any

from supabase import AsyncClient, acreate_client

from app.outreach_message_batch_executor import (
    execute_queued_message_batch,
)
from app.outreach_message_executor import (
    get_outreach_supabase_client,
)
from app.settings import load_settings


MESSAGE_BATCH_TABLE = "outreach_message_batches"
RECONCILE_SECONDS = 300
RECONNECT_SECONDS = 30

logger = logging.getLogger(
    "outreach_message_worker"
)


def find_next_queued_batch(
    client,
) -> dict | None:
    """
    Return the oldest queued batch.

    Prepared batches are intentionally ignored.
    Nothing sends until a batch is explicitly queued.
    """

    response = (
        client
        .table(
            MESSAGE_BATCH_TABLE
        )
        .select(
            (
                "id,"
                "batch_code,"
                "status,"
                "message_template,"
                "queued_at,"
                "created_at"
            )
        )
        .eq(
            "status",
            "queued",
        )
        .order(
            "queued_at",
            desc=False,
        )
        .order(
            "created_at",
            desc=False,
        )
        .limit(
            1
        )
        .execute()
    )

    rows = list(
        response.data
        or []
    )

    if not rows:
        return None

    return dict(
        rows[0]
    )


def drain_queued_batches(client) -> int:
    """Process the current queue, then stop reading until the next wake-up."""
    processed = 0
    while True:
        batch = find_next_queued_batch(client)
        if batch is None:
            return processed

        batch_id = str(batch.get("id") or "").strip()
        batch_code = str(batch.get("batch_code") or batch_id).strip()
        logger.info("Queued message batch found: %s", batch_code)
        result = execute_queued_message_batch(batch_id=batch_id, client=client)
        processed += 1
        logger.info(
            "Message batch completed: %s | sent=%s | failed=%s",
            batch_code, result.get("sent_count"), result.get("failed_count"),
        )


def _payload_record(payload: Any) -> dict:
    if not isinstance(payload, dict):
        return {}
    for key in ("new", "record"):
        if isinstance(payload.get(key), dict):
            return dict(payload[key])
    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("record", "new"):
            if isinstance(data.get(key), dict):
                return dict(data[key])
    return {}


def _wake(queue: asyncio.Queue[bool]) -> None:
    if queue.empty():
        queue.put_nowait(True)


def _handle_realtime_change(payload: Any, queue: asyncio.Queue[bool]) -> None:
    if str(_payload_record(payload).get("status") or "").strip().lower() == "queued":
        _wake(queue)


def _subscribe_callback(queue: asyncio.Queue[bool]):
    def on_status(status: Any, error: Any = None) -> None:
        status_text = str(getattr(status, "value", status) or "").lower()
        if "subscribed" in status_text:
            # One read on each reconnect covers updates missed while offline.
            logger.info("Message Realtime connected; checking queued batches once")
            _wake(queue)
        elif error:
            logger.warning("Message Realtime status=%s | error=%s", status, error)
    return on_status


async def _get_async_client() -> AsyncClient:
    settings = load_settings()
    return await acreate_client(
        settings.outreach_supabase_url,
        settings.outreach_supabase_secret_key,
    )


async def listen_for_batches(queue: asyncio.Queue[bool]) -> None:
    """Listen independently so periodic recovery still works if Realtime fails."""
    while True:
        client = None
        channel = None
        try:
            client = await _get_async_client()
            channel = (
                client.channel("outreach-message-worker")
                .on_postgres_changes(
                    "*", schema="public", table=MESSAGE_BATCH_TABLE,
                    callback=lambda payload: _handle_realtime_change(payload, queue),
                )
            )
            await channel.subscribe(_subscribe_callback(queue))
            await asyncio.Future()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Message Realtime disconnected; retrying")
            await asyncio.sleep(RECONNECT_SECONDS)
        finally:
            if client is not None and channel is not None:
                try:
                    await client.remove_channel(channel)
                except Exception:
                    pass


async def run_forever() -> None:
    """Wake on queued-row events, with a five-minute safety reconciliation."""
    queue: asyncio.Queue[bool] = asyncio.Queue(maxsize=1)
    client = get_outreach_supabase_client()
    listener = asyncio.create_task(listen_for_batches(queue))
    _wake(queue)  # Recover work queued while this process was stopped.
    logger.info("Outreach Message Worker started — Realtime with 5-minute fallback")
    try:
        while True:
            woke = False
            try:
                await asyncio.wait_for(queue.get(), timeout=RECONCILE_SECONDS)
                woke = True
            except asyncio.TimeoutError:
                pass
            try:
                await asyncio.to_thread(drain_queued_batches, client)
            except Exception:
                logger.exception("Message worker iteration failed")
                # Avoid retrying a broken batch in a tight loop.
                await asyncio.sleep(RECONNECT_SECONDS)
            finally:
                if woke:
                    queue.task_done()
    finally:
        listener.cancel()
        try:
            await listener
        except asyncio.CancelledError:
            pass


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    try:
        asyncio.run(run_forever())
    except KeyboardInterrupt:
        logger.info("Outreach Message Worker stopped")


if __name__ == "__main__":
    main()
