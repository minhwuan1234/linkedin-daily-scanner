from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client, create_client

from app.settings import load_settings


MESSAGE_TARGET_TABLE = "outreach_message_targets"
PROSPECT_TABLE = "outreach_prospects"


def _utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def get_client() -> Client:
    settings = load_settings()

    return create_client(
        settings.outreach_supabase_url,
        settings.outreach_supabase_secret_key,
    )


def repair_sent_message_states() -> dict:
    """
    Backfill Accepted Pool message state for messages that were
    already successfully recorded as sent in outreach_message_targets.
    """

    client = get_client()

    response = (
        client
        .table(
            MESSAGE_TARGET_TABLE
        )
        .select(
            "id,prospect_id,completed_at,updated_at"
        )
        .eq(
            "status",
            "sent",
        )
        .execute()
    )

    targets = list(
        response.data
        or []
    )

    repaired = 0
    skipped = 0
    failed = 0

    print("")
    print("MESSAGE STATUS REPAIR")
    print("=====================")
    print("sent targets:", len(targets))

    for index, target in enumerate(
        targets,
        start=1,
    ):
        prospect_id = str(
            target.get("prospect_id")
            or ""
        ).strip()

        if not prospect_id:
            skipped += 1
            continue

        sent_at = (
            target.get("completed_at")
            or target.get("updated_at")
            or _utc_now()
        )

        try:
            result = (
                client
                .table(
                    PROSPECT_TABLE
                )
                .update(
                    {
                        "message_status": "sent",
                        "last_messaged_at": sent_at,
                        "updated_at": _utc_now(),
                    }
                )
                .eq(
                    "id",
                    prospect_id,
                )
                .execute()
            )

            if list(result.data or []):
                repaired += 1
                print(
                    f"[{index}/{len(targets)}] repaired {prospect_id}"
                )
            else:
                failed += 1
                print(
                    f"[{index}/{len(targets)}] no prospect row {prospect_id}"
                )

        except Exception as exc:
            failed += 1
            print(
                f"[{index}/{len(targets)}] ERROR {prospect_id}: {exc}"
            )

    summary = {
        "sent_targets": len(targets),
        "repaired": repaired,
        "skipped": skipped,
        "failed": failed,
    }

    print("")
    print(summary)

    return summary


if __name__ == "__main__":
    repair_sent_message_states()
