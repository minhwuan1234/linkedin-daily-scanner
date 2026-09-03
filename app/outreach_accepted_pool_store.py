from __future__ import annotations

from collections import OrderedDict

from supabase import Client, create_client

from app.settings import load_settings


TARGET_TABLE = "outreach_job_targets"
MESSAGE_TARGET_TABLE = "outreach_message_targets"
MESSAGE_BATCH_TABLE = "outreach_message_batches"


class OutreachAcceptedPoolStoreError(
    RuntimeError
):
    pass


def get_outreach_supabase_client() -> Client:
    """
    Backend-safe Outreach Supabase client.

    Keep Railway independent from LinkedIn browser/action imports.
    """
    settings = load_settings()

    if not settings.outreach_supabase_url:
        raise OutreachAcceptedPoolStoreError(
            "Missing OUTREACH_SUPABASE_URL."
        )

    if not settings.outreach_supabase_secret_key:
        raise OutreachAcceptedPoolStoreError(
            "Missing OUTREACH_SUPABASE_SECRET_KEY."
        )

    return create_client(
        settings.outreach_supabase_url,
        settings.outreach_supabase_secret_key,
    )


def _safe_text(
    value,
) -> str:
    return str(
        value
        or ""
    ).strip()


def _timestamp_value(
    value,
) -> str:
    """
    ISO timestamps are sortable lexicographically when stored in
    the same ISO-8601 format. Empty values sort last in our logic.
    """
    return _safe_text(
        value
    )


def _message_bucket(
    message_status: str,
) -> str:
    """
    For now we only expose the two business buckets requested:

    - not_sent
    - sent

    Any non-sent status remains in not_sent until the later
    messaging workflow defines more granular states.
    """
    status = _safe_text(
        message_status
    ).lower()

    if status == "sent":
        return "sent"

    return "not_sent"


def _dedupe_key(
    *,
    prospect_id: str,
    normalized_url: str,
    linkedin_url: str,
) -> str:
    """
    Primary identity:
        prospect_id

    Safety fallback:
        normalized_url

    Last-resort fallback:
        linkedin_url

    This prevents the same accepted profile from appearing
    multiple times in the Accepted Pool.
    """
    cleaned_prospect_id = _safe_text(
        prospect_id
    )

    if cleaned_prospect_id:
        return (
            "prospect:"
            + cleaned_prospect_id
        )

    cleaned_normalized_url = _safe_text(
        normalized_url
    ).lower()

    if cleaned_normalized_url:
        return (
            "url:"
            + cleaned_normalized_url
        )

    cleaned_linkedin_url = _safe_text(
        linkedin_url
    ).lower().rstrip("/")

    return (
        "raw:"
        + cleaned_linkedin_url
    )


def _normalize_pool_row(
    row: dict,
) -> dict:
    prospect = (
        row.get(
            "outreach_prospects"
        )
        or {}
    )

    message_status = _safe_text(
        prospect.get(
            "message_status"
        )
    )

    return {
        "target_id": _safe_text(
            row.get(
                "id"
            )
        ),
        "job_id": _safe_text(
            row.get(
                "job_id"
            )
        ),
        "prospect_id": _safe_text(
            row.get(
                "prospect_id"
            )
        ),
        "assigned_account_id": _safe_text(
            row.get(
                "assigned_account_id"
            )
        ),
        "acceptance_status": _safe_text(
            row.get(
                "acceptance_status"
            )
        ),
        "acceptance_checked_at": (
            row.get(
                "acceptance_checked_at"
            )
        ),
        "accepted_at": (
            row.get(
                "accepted_at"
            )
        ),
        "acceptance_check_count": int(
            row.get(
                "acceptance_check_count",
                0,
            )
            or 0
        ),
        "linkedin_url": _safe_text(
            prospect.get(
                "linkedin_url"
            )
        ),
        "normalized_url": _safe_text(
            prospect.get(
                "normalized_url"
            )
        ),
        "connect_status": _safe_text(
            prospect.get(
                "connect_status"
            )
        ),
        "message_status": message_status,
        "message_bucket": (
            _message_bucket(
                message_status
            )
        ),
        "last_messaged_at": (
            prospect.get(
                "last_messaged_at"
            )
        ),
        "prospect_created_at": (
            prospect.get(
                "created_at"
            )
        ),
        "prospect_updated_at": (
            prospect.get(
                "updated_at"
            )
        ),
    }



def _chunked(
    values: list[str],
    size: int = 200,
):
    for start in range(
        0,
        len(values),
        size,
    ):
        yield values[
            start:start + size
        ]


def _load_existing_send_batches(
    *,
    client: Client,
    prospect_ids: list[str],
) -> dict[str, dict]:
    """
    Resolve the existing Message Batch for Accepted Pool rows.

    No new "send id" is created here.

    Existing identity:
        outreach_message_targets.batch_id
            -> outreach_message_batches.id / batch_code

    If a prospect has appeared in more than one message batch, Recipients
    shows the newest assignment because that is the current/latest send
    context for the profile.

    The query is restricted to prospect_ids already loaded for Accepted Pool;
    it never scans the whole message-target table.
    """

    cleaned_ids = list(
        dict.fromkeys(
            _safe_text(value)
            for value in prospect_ids
            if _safe_text(value)
        )
    )

    if not cleaned_ids:
        return {}

    latest_target_by_prospect: dict[
        str,
        dict,
    ] = {}

    for chunk in _chunked(
        cleaned_ids
    ):
        response = (
            client
            .table(
                MESSAGE_TARGET_TABLE
            )
            .select(
                (
                    "id,"
                    "batch_id,"
                    "prospect_id,"
                    "status,"
                    "created_at,"
                    "updated_at"
                )
            )
            .in_(
                "prospect_id",
                chunk,
            )
            .order(
                "created_at",
                desc=True,
            )
            .execute()
        )

        for row in list(
            response.data
            or []
        ):
            prospect_id = _safe_text(
                row.get(
                    "prospect_id"
                )
            )

            if (
                not prospect_id
                or prospect_id
                in latest_target_by_prospect
            ):
                continue

            latest_target_by_prospect[
                prospect_id
            ] = dict(
                row
            )

    batch_ids = list(
        dict.fromkeys(
            _safe_text(
                row.get(
                    "batch_id"
                )
            )
            for row in (
                latest_target_by_prospect
                .values()
            )
            if _safe_text(
                row.get(
                    "batch_id"
                )
            )
        )
    )

    batch_by_id: dict[
        str,
        dict,
    ] = {}

    for chunk in _chunked(
        batch_ids
    ):
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
                    "created_at"
                )
            )
            .in_(
                "id",
                chunk,
            )
            .execute()
        )

        for row in list(
            response.data
            or []
        ):
            batch_id = _safe_text(
                row.get(
                    "id"
                )
            )

            if batch_id:
                batch_by_id[
                    batch_id
                ] = dict(
                    row
                )

    result: dict[
        str,
        dict,
    ] = {}

    for prospect_id, target in (
        latest_target_by_prospect
        .items()
    ):
        batch_id = _safe_text(
            target.get(
                "batch_id"
            )
        )

        batch = (
            batch_by_id.get(
                batch_id
            )
            or {}
        )

        result[
            prospect_id
        ] = {
            "message_batch_id": (
                batch_id
            ),
            "message_batch_code": (
                _safe_text(
                    batch.get(
                        "batch_code"
                    )
                )
            ),
            "message_batch_status": (
                _safe_text(
                    batch.get(
                        "status"
                    )
                )
            ),
            "message_target_id": (
                _safe_text(
                    target.get(
                        "id"
                    )
                )
            ),
            "message_target_status": (
                _safe_text(
                    target.get(
                        "status"
                    )
                )
            ),
        }

    return result


def get_accepted_pool(
    *,
    client: Client | None = None,
) -> dict:
    """
    Build the Accepted Pool directly from current source data.

    Source of truth:
        outreach_job_targets.acceptance_status == accepted

    Important:
    - no separate accepted-pool table;
    - every Acceptance Check update is visible on the next API read;
    - one profile appears only once;
    - primary dedupe key is prospect_id;
    - normalized_url is the safety fallback;
    - the accepted target with the latest accepted/check timestamp wins.

    Return:
        {
            "summary": {
                "total": ...,
                "not_sent": ...,
                "sent": ...
            },
            "items": [...]
        }
    """
    active_client = (
        client
        if client is not None
        else get_outreach_supabase_client()
    )

    try:
        response = (
            active_client
            .table(
                TARGET_TABLE
            )
            .select(
                (
                    "id,"
                    "job_id,"
                    "prospect_id,"
                    "assigned_account_id,"
                    "acceptance_status,"
                    "acceptance_checked_at,"
                    "accepted_at,"
                    "acceptance_check_count,"
                    "outreach_prospects("
                    "id,"
                    "linkedin_url,"
                    "normalized_url,"
                    "connect_status,"
                    "message_status,"
                    "last_messaged_at,"
                    "created_at,"
                    "updated_at"
                    ")"
                )
            )
            .eq(
                "acceptance_status",
                "accepted",
            )
            .order(
                "accepted_at",
                desc=True,
            )
            .execute()
        )

    except Exception as exc:
        raise OutreachAcceptedPoolStoreError(
            "Could not load Accepted Pool: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    rows = list(
        response.data
        or []
    )

    # OrderedDict preserves the first row we keep.
    # Because the query is newest-first, latest accepted state wins.
    unique: OrderedDict[
        str,
        dict,
    ] = OrderedDict()

    for raw_row in rows:
        item = _normalize_pool_row(
            raw_row
        )

        # Pool rows must remain actionable for the later messaging step.
        if not item[
            "assigned_account_id"
        ]:
            continue

        if not item[
            "linkedin_url"
        ]:
            continue

        key = _dedupe_key(
            prospect_id=(
                item[
                    "prospect_id"
                ]
            ),
            normalized_url=(
                item[
                    "normalized_url"
                ]
            ),
            linkedin_url=(
                item[
                    "linkedin_url"
                ]
            ),
        )

        existing = unique.get(
            key
        )

        if existing is None:
            unique[
                key
            ] = item
            continue

        # Extra safety if source ordering is ever inconsistent:
        # keep whichever accepted/check timestamp is newer.
        existing_time = max(
            _timestamp_value(
                existing.get(
                    "accepted_at"
                )
            ),
            _timestamp_value(
                existing.get(
                    "acceptance_checked_at"
                )
            ),
        )

        candidate_time = max(
            _timestamp_value(
                item.get(
                    "accepted_at"
                )
            ),
            _timestamp_value(
                item.get(
                    "acceptance_checked_at"
                )
            ),
        )

        if candidate_time > existing_time:
            unique[
                key
            ] = item

    items = list(
        unique.values()
    )

    # Stable newest-first output.
    items.sort(
        key=lambda item: max(
            _timestamp_value(
                item.get(
                    "accepted_at"
                )
            ),
            _timestamp_value(
                item.get(
                    "acceptance_checked_at"
                )
            ),
        ),
        reverse=True,
    )

    existing_send_batches = (
        _load_existing_send_batches(
            client=active_client,
            prospect_ids=[
                _safe_text(
                    item.get(
                        "prospect_id"
                    )
                )
                for item in items
            ],
        )
    )

    for item in items:
        prospect_id = _safe_text(
            item.get(
                "prospect_id"
            )
        )

        send_batch = (
            existing_send_batches.get(
                prospect_id
            )
            or {}
        )

        item.update(
            {
                "message_batch_id": (
                    _safe_text(
                        send_batch.get(
                            "message_batch_id"
                        )
                    )
                ),
                "message_batch_code": (
                    _safe_text(
                        send_batch.get(
                            "message_batch_code"
                        )
                    )
                ),
                "message_batch_status": (
                    _safe_text(
                        send_batch.get(
                            "message_batch_status"
                        )
                    )
                ),
                "message_target_id": (
                    _safe_text(
                        send_batch.get(
                            "message_target_id"
                        )
                    )
                ),
                "message_target_status": (
                    _safe_text(
                        send_batch.get(
                            "message_target_status"
                        )
                    )
                ),
            }
        )

    sent_count = sum(
        1
        for item in items
        if item[
            "message_bucket"
        ] == "sent"
    )

    not_sent_count = (
        len(items)
        - sent_count
    )

    return {
        "summary": {
            "total": len(
                items
            ),
            "not_sent": (
                not_sent_count
            ),
            "sent": sent_count,
        },
        "items": items,
    }
