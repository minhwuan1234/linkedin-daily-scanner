from __future__ import annotations

import argparse
import logging
import os
import time

from app.linkedin_message_sender import send_message_once
from app.linkedin_profile_message import get_profile_name
from app.outreach_account_pool import OutreachAccountPool
from app.outreach_message_executor import get_outreach_supabase_client
from app.outreach_reply_send_store import (
    claim_reply_send,
    finish_reply_send,
    load_queued_reply_sends,
)


DEFAULT_ACCOUNT_ID = "outreach_account_01"
BETWEEN_SENDS_SECONDS = 2.5
IDLE_POLL_SECONDS = 3

logger = logging.getLogger("outreach_reply_send_worker")


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


def run_forever(account_id: str) -> None:
    """Keep the account worker active while opening Chrome only for queued jobs."""

    logger.info(
        "Reply send worker active | account=%s | poll_seconds=%s",
        account_id,
        IDLE_POLL_SECONDS,
    )
    while True:
        try:
            run_once(account_id, quiet_empty=True)
        except KeyboardInterrupt:
            raise
        except Exception:
            logger.exception("Reply send worker poll failed | account=%s", account_id)
        time.sleep(IDLE_POLL_SECONDS)


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
    args = _parse_args()
    account_id = str(args.account_id).strip()
    try:
        if args.once:
            run_once(account_id)
        else:
            run_forever(account_id)
    except KeyboardInterrupt:
        logger.info("Reply send worker stopped | account=%s", account_id)


if __name__ == "__main__":
    main()
