from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from app.linkedin_session_checker import (
    check_outreach_account_session,
)
from app.outreach_account_pool import OutreachAccountPool
from app.outreach_session_status import (
    SESSION_TABLE,
    get_outreach_supabase_client,
)


IDLE_POLL_SECONDS = 3

logger = logging.getLogger("outreach_session_worker")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def claim_next_session_check(client) -> dict | None:
    response = (
        client
        .table(SESSION_TABLE)
        .select("account_id,display_name,status,requested_at")
        .eq("status", "pending")
        .order("requested_at", desc=False)
        .limit(1)
        .execute()
    )

    rows = list(response.data or [])
    if not rows:
        return None

    row = dict(rows[0])
    account_id = str(row.get("account_id") or "").strip()
    now = _utc_now_iso()

    update = (
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

    updated_rows = list(update.data or [])
    if not updated_rows:
        return None

    return dict(updated_rows[0])


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
                "last_error": detail if status in {"unknown", "failed", "busy", "checkpoint"} else None,
                "updated_at": now,
            }
        )
        .eq("account_id", account_id)
        .execute()
    )


def fail_session_check(client, *, account_id: str, error: Exception) -> None:
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


def run_forever() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    client = get_outreach_supabase_client()
    pool = OutreachAccountPool()

    logger.info("Outreach Session Worker started.")

    while True:
        account_id = ""

        try:
            request = claim_next_session_check(client)

            if request is None:
                time.sleep(IDLE_POLL_SECONDS)
                continue

            account_id = str(request.get("account_id") or "").strip()
            account = pool.get_account(account_id)

            logger.info("Checking LinkedIn session: %s", account_id)

            result = check_outreach_account_session(account)

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

        except KeyboardInterrupt:
            logger.info("Outreach Session Worker stopped.")
            raise

        except Exception as exc:
            logger.exception("Session worker iteration failed.")

            if account_id:
                try:
                    fail_session_check(
                        client,
                        account_id=account_id,
                        error=exc,
                    )
                except Exception:
                    logger.exception("Could not persist session check failure.")

            time.sleep(IDLE_POLL_SECONDS)


if __name__ == "__main__":
    run_forever()
