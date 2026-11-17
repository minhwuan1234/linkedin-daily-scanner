from __future__ import annotations

import asyncio
import logging
from typing import Any


from app.outreach_message_batch_executor import (
    execute_queued_message_batch,
)
from app.outreach_message_executor import (
    get_outreach_supabase_client,
)


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
            "Message batch %s: %s | sent=%s | failed=%s | error=%s",
            "completed" if result.get("ok") else "failed", batch_code,
            result.get("sent_count"), result.get("failed_count"), result.get("error") or "-",
        )














async def run_forever() -> None:
    client = get_outreach_supabase_client()
    logger.info("Outreach Message Worker started — PostgreSQL polling every 5 seconds")
    while True:
        try:
            await asyncio.to_thread(drain_queued_batches, client)
        except Exception:
            logger.exception("Message worker iteration failed")
            await asyncio.sleep(RECONNECT_SECONDS)
        await asyncio.sleep(5)



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
