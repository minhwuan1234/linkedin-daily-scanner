from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from supabase import Client, create_client

from app.outreach_accepted_pool_store import (
    get_accepted_pool,
)
from app.settings import load_settings


MESSAGE_BATCH_TABLE = (
    "outreach_message_batches"
)

MESSAGE_TARGET_TABLE = (
    "outreach_message_targets"
)

LOCAL_TIMEZONE = ZoneInfo(
    "Asia/Ho_Chi_Minh"
)


class OutreachMessagePreparationStoreError(
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


# =========================================================
# SUPABASE
# =========================================================

def get_outreach_supabase_client() -> Client:
    """
    Backend-safe client.

    This preparation layer only reads/writes Supabase.
    It does NOT import or run LinkedIn browser code.
    """
    settings = load_settings()

    if not settings.outreach_supabase_url:
        raise OutreachMessagePreparationStoreError(
            "Missing OUTREACH_SUPABASE_URL."
        )

    if not settings.outreach_supabase_secret_key:
        raise OutreachMessagePreparationStoreError(
            "Missing OUTREACH_SUPABASE_SECRET_KEY."
        )

    return create_client(
        settings.outreach_supabase_url,
        settings.outreach_supabase_secret_key,
    )


# =========================================================
# BATCH CODE
# =========================================================

def _build_batch_code(
    *,
    client: Client,
) -> str:
    """
    Format:
        MSG-YYYYMMDD-01
        MSG-YYYYMMDD-02
        ...
    """
    now = datetime.now(
        LOCAL_TIMEZONE
    )

    date_code = now.strftime(
        "%Y%m%d"
    )

    prefix = (
        f"MSG-{date_code}"
    )

    response = (
        client.table(
            MESSAGE_BATCH_TABLE
        )
        .select(
            "batch_code"
        )
        .like(
            "batch_code",
            f"{prefix}-%",
        )
        .execute()
    )

    rows = list(
        response.data
        or []
    )

    highest_sequence = 0

    for row in rows:
        batch_code = _safe_text(
            row.get(
                "batch_code"
            )
        )

        if not batch_code:
            continue

        try:
            sequence = int(
                batch_code.rsplit(
                    "-",
                    1,
                )[1]
            )

        except (
            IndexError,
            ValueError,
        ):
            continue

        highest_sequence = max(
            highest_sequence,
            sequence,
        )

    return (
        f"{prefix}-"
        f"{highest_sequence + 1:02d}"
    )


# =========================================================
# ALREADY PREPARED PROSPECTS
# =========================================================

def _load_prepared_prospect_ids(
    *,
    client: Client,
) -> set[str]:
    """
    Profiles already snapshot into a currently prepared message
    batch are excluded from future Prepare All runs.

    This prevents:
        Batch #1 -> Prospect A
        Batch #2 -> Prospect A again

    before the messaging phase has even started.
    """
    response = (
        client.table(
            MESSAGE_TARGET_TABLE
        )
        .select(
            "prospect_id,status"
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

    return {
        _safe_text(
            row.get(
                "prospect_id"
            )
        )
        for row in rows
        if _safe_text(
            row.get(
                "prospect_id"
            )
        )
    }


# =========================================================
# ELIGIBLE RECIPIENTS
# =========================================================

def get_message_preparation_candidates(
    *,
    client: Client | None = None,
) -> dict:
    """
    Build the exact recipient set that would be snapshotted now.

    Eligibility:
    - Acceptance Pool item exists
    - message_bucket == not_sent
    - prospect_id exists
    - assigned_account_id exists
    - linkedin_url exists
    - not already in another prepared message batch

    This function does NOT create a batch.
    """
    active_client = (
        client
        if client is not None
        else get_outreach_supabase_client()
    )

    accepted_pool = (
        get_accepted_pool(
            client=active_client
        )
    )

    pool_items = (
        accepted_pool.get(
            "items"
        )
        or []
    )

    already_prepared = (
        _load_prepared_prospect_ids(
            client=active_client
        )
    )

    candidates: list[dict] = []

    for item in pool_items:
        if (
            _safe_text(
                item.get(
                    "message_bucket"
                )
            ).lower()
            != "not_sent"
        ):
            continue

        prospect_id = _safe_text(
            item.get(
                "prospect_id"
            )
        )

        source_target_id = _safe_text(
            item.get(
                "target_id"
            )
        )

        account_id = _safe_text(
            item.get(
                "assigned_account_id"
            )
        )

        linkedin_url = _safe_text(
            item.get(
                "linkedin_url"
            )
        )

        if (
            not prospect_id
            or not source_target_id
            or not account_id
            or not linkedin_url
        ):
            continue

        if prospect_id in already_prepared:
            continue

        candidates.append(
            {
                "prospect_id": (
                    prospect_id
                ),
                "source_target_id": (
                    source_target_id
                ),
                "assigned_account_id": (
                    account_id
                ),
                "linkedin_url": (
                    linkedin_url
                ),
                "normalized_url": _safe_text(
                    item.get(
                        "normalized_url"
                    )
                ),
                "accepted_at": (
                    item.get(
                        "accepted_at"
                    )
                ),
            }
        )

    return {
        "count": len(
            candidates
        ),
        "items": candidates,
    }


# =========================================================
# PREPARE ALL
# =========================================================

def prepare_all_unsent_accepted(
    *,
    client: Client | None = None,
) -> dict:
    """
    Snapshot ALL currently eligible accepted + not-sent profiles.

    IMPORTANT:
    This is preparation only.

    It does NOT:
    - send a message;
    - start a browser;
    - queue a messaging worker;
    - write message text/template;
    - change outreach_prospects.message_status.

    Result:
        one outreach_message_batches row
        +
        N outreach_message_targets rows
        all status='prepared'
    """
    active_client = (
        client
        if client is not None
        else get_outreach_supabase_client()
    )

    candidate_result = (
        get_message_preparation_candidates(
            client=active_client
        )
    )

    candidates = (
        candidate_result[
            "items"
        ]
    )

    if not candidates:
        return {
            "created": False,
            "reason": (
                "no_eligible_recipients"
            ),
            "batch": None,
            "target_count": 0,
        }

    batch_code = (
        _build_batch_code(
            client=active_client
        )
    )

    now = _utc_now()

    batch_response = (
        active_client.table(
            MESSAGE_BATCH_TABLE
        )
        .insert(
            {
                "batch_code": batch_code,
                "status": "prepared",
                "target_count": 0,
                "created_at": now,
                "updated_at": now,
            }
        )
        .execute()
    )

    batch_rows = list(
        batch_response.data
        or []
    )

    if not batch_rows:
        raise OutreachMessagePreparationStoreError(
            "Could not create message preparation batch."
        )

    batch = batch_rows[0]

    batch_id = _safe_text(
        batch.get(
            "id"
        )
    )

    if not batch_id:
        raise OutreachMessagePreparationStoreError(
            "Created message batch has no id."
        )

    target_rows = [
        {
            "batch_id": batch_id,
            "prospect_id": (
                item[
                    "prospect_id"
                ]
            ),
            "source_target_id": (
                item[
                    "source_target_id"
                ]
            ),
            "assigned_account_id": (
                item[
                    "assigned_account_id"
                ]
            ),
            "linkedin_url": (
                item[
                    "linkedin_url"
                ]
            ),
            "normalized_url": (
                item[
                    "normalized_url"
                ]
                or None
            ),
            "status": "prepared",
            "created_at": now,
            "updated_at": now,
        }
        for item in candidates
    ]

    try:
        target_response = (
            active_client.table(
                MESSAGE_TARGET_TABLE
            )
            .insert(
                target_rows
            )
            .execute()
        )

        inserted_targets = list(
            target_response.data
            or []
        )

        inserted_count = len(
            inserted_targets
        )

        if inserted_count != len(
            target_rows
        ):
            raise OutreachMessagePreparationStoreError(
                "Prepared target insert count mismatch: "
                f"expected {len(target_rows)}, "
                f"got {inserted_count}."
            )

        (
            active_client.table(
                MESSAGE_BATCH_TABLE
            )
            .update(
                {
                    "target_count": (
                        inserted_count
                    ),
                    "updated_at": (
                        _utc_now()
                    ),
                }
            )
            .eq(
                "id",
                batch_id,
            )
            .execute()
        )

    except Exception:
        # Keep preparation all-or-nothing from the application's
        # perspective. Deleting the batch cascades its inserted targets.
        try:
            (
                active_client.table(
                    MESSAGE_BATCH_TABLE
                )
                .delete()
                .eq(
                    "id",
                    batch_id,
                )
                .execute()
            )
        except Exception:
            pass

        raise

    batch[
        "target_count"
    ] = inserted_count

    return {
        "created": True,
        "reason": None,
        "batch": batch,
        "target_count": (
            inserted_count
        ),
    }


# =========================================================
# PREPARED BATCH READ API
# =========================================================

def list_prepared_message_batches(
    *,
    client: Client | None = None,
    limit: int = 50,
) -> list[dict]:
    """
    List recent message-preparation batches.

    Preparation phase only:
    this does NOT trigger messaging.
    """
    active_client = (
        client
        if client is not None
        else get_outreach_supabase_client()
    )

    safe_limit = max(
        1,
        min(
            int(limit),
            100,
        ),
    )

    response = (
        active_client.table(
            MESSAGE_BATCH_TABLE
        )
        .select(
            (
                "id,"
                "batch_code,"
                "status,"
                "target_count,"
                "created_at,"
                "updated_at"
            )
        )
        .order(
            "created_at",
            desc=True,
        )
        .limit(
            safe_limit
        )
        .execute()
    )

    return list(
        response.data
        or []
    )


def get_prepared_message_batch(
    batch_id: str,
    *,
    client: Client | None = None,
) -> dict | None:
    """
    Load one prepared batch plus its frozen recipient snapshot.
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
        raise OutreachMessagePreparationStoreError(
            "Missing message batch id."
        )

    batch_response = (
        active_client.table(
            MESSAGE_BATCH_TABLE
        )
        .select(
            (
                "id,"
                "batch_code,"
                "status,"
                "target_count,"
                "created_at,"
                "updated_at"
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
        return None

    target_response = (
        active_client.table(
            MESSAGE_TARGET_TABLE
        )
        .select(
            (
                "id,"
                "batch_id,"
                "prospect_id,"
                "source_target_id,"
                "assigned_account_id,"
                "linkedin_url,"
                "normalized_url,"
                "status,"
                "created_at,"
                "updated_at"
            )
        )
        .eq(
            "batch_id",
            cleaned_batch_id,
        )
        .order(
            "created_at",
            desc=False,
        )
        .execute()
    )

    batch = dict(
        batch_rows[0]
    )

    batch[
        "targets"
    ] = list(
        target_response.data
        or []
    )

    return batch
