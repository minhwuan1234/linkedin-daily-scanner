"""Optional Supabase heartbeat for work without a dedicated job record."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from threading import Event, Thread

from app.outreach_dashboard_store import get_outreach_client


logger = logging.getLogger(__name__)
TABLE = "outreach_worker_activity"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def worker_heartbeat(task_key: str, account_id: str):
    """Keep a running row fresh; never block the underlying worker on telemetry."""
    row_id = None
    stop = Event()
    thread = None
    try:
        result = get_outreach_client().table(TABLE).insert({
            "task_key": task_key,
            "account_id": account_id,
            "status": "running",
            "started_at": _now(),
            "updated_at": _now(),
        }).execute()
        row_id = (result.data or [{}])[0].get("id")
    except Exception:
        logger.warning("Worker activity table unavailable; live %s status is not reported", task_key)

    if row_id:
        def refresh() -> None:
            while not stop.wait(30):
                try:
                    get_outreach_client().table(TABLE).update({"updated_at": _now()}).eq("id", row_id).execute()
                except Exception:
                    logger.warning("Could not refresh %s heartbeat", task_key)

        thread = Thread(target=refresh, daemon=True)
        thread.start()

    try:
        yield
    finally:
        stop.set()
        if thread:
            thread.join(timeout=2)
        if row_id:
            try:
                get_outreach_client().table(TABLE).update({
                    "status": "finished",
                    "finished_at": _now(),
                    "updated_at": _now(),
                }).eq("id", row_id).execute()
            except Exception:
                logger.warning("Could not close %s heartbeat", task_key)
