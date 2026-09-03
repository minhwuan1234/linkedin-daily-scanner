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


def _load_latest_message_assignments(
    *,
    client: Client,
    prospect_ids: list[str],
) -> dict[str, dict]:
    """
    Load only message-target metadata for prospects already present in the
    Accepted Pool. This avoids a full message-target table scan.

    One prospect may eventually participate in multiple campaigns. The newest
    target is the identity shown in the Recipients table.
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

    target_rows: list[dict] = []

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
                    "send_code,"
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

        target_rows.extend(
            list(
                response.data
                or []
            )
        )

    latest_by_prospect: dict[
        str,
        dict,
    ] = {}

    for row in target_rows:
        prospect_id = _safe_text(
            row.get(
                "prospect_id"
            )
        )

        if not prospect_id:
            continue

        existing = latest_by_prospect.get(
            prospect_id
        )

        row_time = max(
            _timestamp_value(
                row.get(
                    "updated_at"
                )
            ),
            _timestamp_value(
                row.get(
                    "created_at"
                )
            ),
        )

        existing_time = (
            max(
                _timestamp_value(
                    existing.get(
                        "updated_at"
                    )
                ),
                _timestamp_value(
                    existing.get(
                        "created_at"
                    )
                ),
            )
            if existing
            else ""
        )

        if (
            existing is None
            or row_time > existing_time
        ):
            latest_by_prospect[
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
            for row in latest_by_prospect.values()
            if _safe_text(
                row.get(
                    "batch_id"
                )
            )
        )
    )

    batches_by_id: dict[
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
                    "campaign_code,"
                    "campaign_name,"
                    "status"
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
                batches_by_id[
                    batch_id
                ] = dict(
                    row
                )

    result: dict[
        str,
        dict,
    ] = {}

    for prospect_id, target in (
        latest_by_prospect.items()
    ):
        batch_id = _safe_text(
            target.get(
                "batch_id"
            )
        )

        batch = (
            batches_by_id.get(
                batch_id
            )
            or {}
        )

        result[
            prospect_id
        ] = {
            "message_target_id": _safe_text(
                target.get(
                    "id"
                )
            ),
            "send_code": _safe_text(
                target.get(
                    "send_code"
                )
            ),
            "message_target_status": _safe_text(
                target.get(
                    "status"
                )
            ),
            "campaign_id": batch_id,
            "campaign_code": _safe_text(
                batch.get(
                    "campaign_code"
                )
            ),
            "campaign_name": _safe_text(
                batch.get(
                    "campaign_name"
                )
            ),
            "campaign_status": _safe_text(
                batch.get(
                    "status"
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

    message_assignments = (
        _load_latest_message_assignments(
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

        assignment = (
            message_assignments.get(
                prospect_id
            )
            or {}
        )

        item.update(
            {
                "message_target_id": _safe_text(
                    assignment.get(
                        "message_target_id"
                    )
                ),
                "send_code": _safe_text(
                    assignment.get(
                        "send_code"
                    )
                ),
                "message_target_status": _safe_text(
                    assignment.get(
                        "message_target_status"
                    )
                ),
                "campaign_id": _safe_text(
                    assignment.get(
                        "campaign_id"
                    )
                ),
                "campaign_code": _safe_text(
                    assignment.get(
                        "campaign_code"
                    )
                ),
                "campaign_name": _safe_text(
                    assignment.get(
                        "campaign_name"
                    )
                ),
                "campaign_status": _safe_text(
                    assignment.get(
                        "campaign_status"
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
