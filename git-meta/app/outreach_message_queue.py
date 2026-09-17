from __future__ import annotations

from datetime import datetime, timezone

from app.outreach_message_executor import (
    get_outreach_supabase_client,
)


MESSAGE_BATCH_TABLE = "outreach_message_batches"
MESSAGE_TARGET_TABLE = "outreach_message_targets"


class OutreachMessageQueueError(
    RuntimeError
):
    pass


def _utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def _safe_text(
    value,
) -> str:
    return str(
        value
        or ""
    ).strip()


def inspect_prepared_batch(
    batch_id: str,
    *,
    client=None,
) -> dict:
    """
    Read one prepared batch and count its prepared targets.

    No status is changed.
    No LinkedIn action happens.
    """

    active_client = (
        client
        if client is not None
        else get_outreach_supabase_client()
    )

    cleaned_batch_id = _safe_text(
        batch_id
    )

    if not cleaned_batch_id:
        raise ValueError(
            "batch_id is required."
        )

    batch_response = (
        active_client
        .table(
            MESSAGE_BATCH_TABLE
        )
        .select(
            (
                "id,"
                "batch_code,"
                "status,"
                "message_template,"
                "target_count,"
                "created_at"
            )
        )
        .eq(
            "id",
            cleaned_batch_id,
        )
        .limit(
            1
        )
        .execute()
    )

    batch_rows = list(
        batch_response.data
        or []
    )

    if not batch_rows:
        raise OutreachMessageQueueError(
            "Message batch not found: "
            f"{cleaned_batch_id}"
        )

    batch = dict(
        batch_rows[0]
    )

    target_response = (
        active_client
        .table(
            MESSAGE_TARGET_TABLE
        )
        .select(
            (
                "id,"
                "assigned_account_id,"
                "linkedin_url,"
                "status"
            )
        )
        .eq(
            "batch_id",
            cleaned_batch_id,
        )
        .eq(
            "status",
            "prepared",
        )
        .order(
            "created_at",
            desc=False,
        )
        .execute()
    )

    prepared_targets = list(
        target_response.data
        or []
    )

    return {
        "batch": batch,
        "prepared_target_count": (
            len(
                prepared_targets
            )
        ),
        "prepared_targets": (
            prepared_targets
        ),
    }


def queue_prepared_batch_for_test(
    *,
    batch_id: str,
    template: str,
    max_targets: int = 2,
    client=None,
) -> dict:
    """
    STEP 5 — queue one SMALL prepared batch.

    Safety rule:
    - default max_targets = 2
    - if the batch has more than max_targets prepared targets,
      refuse to queue it.

    This function DOES NOT send LinkedIn messages itself.
    The always-on outreach_message_worker.py will pick up the
    batch after its status becomes queued.
    """

    active_client = (
        client
        if client is not None
        else get_outreach_supabase_client()
    )

    cleaned_template = str(
        template
        or ""
    )

    if not cleaned_template.strip():
        raise ValueError(
            "template is required."
        )

    if max_targets < 1:
        raise ValueError(
            "max_targets must be >= 1."
        )

    inspection = inspect_prepared_batch(
        batch_id,
        client=active_client,
    )

    batch = inspection[
        "batch"
    ]

    status = _safe_text(
        batch.get(
            "status"
        )
    ).lower()

    if status != "prepared":
        raise OutreachMessageQueueError(
            "Batch is not prepared: "
            f"{batch_id} | status={status}"
        )

    prepared_target_count = int(
        inspection[
            "prepared_target_count"
        ]
    )

    if prepared_target_count == 0:
        raise OutreachMessageQueueError(
            "Batch has no prepared targets."
        )

    if prepared_target_count > max_targets:
        raise OutreachMessageQueueError(
            (
                "Safety stop: batch has "
                f"{prepared_target_count} prepared targets, "
                f"but max_targets={max_targets}."
            )
        )

    now = _utc_now()

    response = (
        active_client
        .table(
            MESSAGE_BATCH_TABLE
        )
        .update(
            {
                "status": "queued",
                "message_template": (
                    cleaned_template
                ),
                "queued_at": now,
                "last_error": None,
                "updated_at": now,
            }
        )
        .eq(
            "id",
            _safe_text(
                batch_id
            ),
        )
        .eq(
            "status",
            "prepared",
        )
        .execute()
    )

    rows = list(
        response.data
        or []
    )

    if not rows:
        raise OutreachMessageQueueError(
            "Could not queue batch. "
            "Its status may have changed."
        )

    return {
        "ok": True,
        "batch_id": _safe_text(
            batch_id
        ),
        "batch_code": _safe_text(
            batch.get(
                "batch_code"
            )
        ),
        "status": "queued",
        "prepared_target_count": (
            prepared_target_count
        ),
        "message_template": (
            cleaned_template
        ),
    }


def print_prepared_batch(
    batch_id: str,
) -> None:
    result = inspect_prepared_batch(
        batch_id
    )

    batch = result[
        "batch"
    ]

    print("")
    print(
        "MESSAGE BATCH INSPECTION"
    )
    print(
        "========================"
    )
    print(
        f"batch_id: {batch.get('id')}"
    )
    print(
        f"batch_code: {batch.get('batch_code')}"
    )
    print(
        f"status: {batch.get('status')}"
    )
    print(
        "prepared_target_count: "
        f"{result['prepared_target_count']}"
    )

    print("")
    print(
        "TARGETS"
    )
    print(
        "-------"
    )

    for target in result[
        "prepared_targets"
    ]:
        print(
            (
                f"{target.get('id')} | "
                f"{target.get('assigned_account_id')} | "
                f"{target.get('linkedin_url')}"
            )
        )


def print_queue_test_result(
    *,
    batch_id: str,
    template: str,
    max_targets: int = 2,
) -> None:
    result = queue_prepared_batch_for_test(
        batch_id=batch_id,
        template=template,
        max_targets=max_targets,
    )

    print("")
    print(
        "MESSAGE BATCH QUEUED"
    )
    print(
        "===================="
    )
    print(
        f"batch_id: {result['batch_id']}"
    )
    print(
        f"batch_code: {result['batch_code']}"
    )
    print(
        f"status: {result['status']}"
    )
    print(
        "prepared_target_count: "
        f"{result['prepared_target_count']}"
    )
