from __future__ import annotations

import logging
import time

from app.outreach_message_batch_executor import (
    execute_queued_message_batch,
)
from app.outreach_message_executor import (
    get_outreach_supabase_client,
)


IDLE_POLL_SECONDS = 10

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
            "outreach_message_batches"
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


def run_forever() -> None:
    """
    Always-on Mac worker.

    Loop:
        poll Supabase
        -> no queued batch: sleep
        -> queued batch: execute it
        -> continue polling

    A failed batch is logged and the worker continues.
    """

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(message)s"
        ),
    )

    client = get_outreach_supabase_client()

    logger.info(
        "Outreach Message Worker started."
    )

    while True:
        try:
            batch = find_next_queued_batch(
                client
            )

            if batch is None:
                time.sleep(
                    IDLE_POLL_SECONDS
                )
                continue

            batch_id = str(
                batch.get(
                    "id"
                )
                or ""
            ).strip()

            batch_code = str(
                batch.get(
                    "batch_code"
                )
                or batch_id
            ).strip()

            logger.info(
                "Queued message batch found: %s",
                batch_code,
            )

            result = execute_queued_message_batch(
                batch_id=batch_id,
                client=client,
            )

            logger.info(
                (
                    "Message batch completed: %s | "
                    "sent=%s | failed=%s"
                ),
                batch_code,
                result.get(
                    "sent_count"
                ),
                result.get(
                    "failed_count"
                ),
            )

        except KeyboardInterrupt:
            logger.info(
                "Outreach Message Worker stopped."
            )
            raise

        except Exception:
            logger.exception(
                "Message worker iteration failed."
            )

            time.sleep(
                IDLE_POLL_SECONDS
            )


if __name__ == "__main__":
    run_forever()
