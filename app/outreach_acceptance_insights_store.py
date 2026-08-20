from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client, create_client

from app.settings import load_settings


TARGET_TABLE = "outreach_job_targets"
JOB_TABLE = "outreach_jobs"

PAGE_SIZE = 1000


class OutreachAcceptanceInsightsStoreError(
    RuntimeError
):
    pass


def _safe_text(
    value,
) -> str:
    return str(
        value
        or ""
    ).strip()


def _utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def get_outreach_supabase_client() -> Client:
    """
    Railway-safe Outreach Supabase client.

    This module does not import Playwright, LinkedIn browser
    code, or Mac worker code.
    """
    settings = load_settings()

    if not settings.outreach_supabase_url:
        raise OutreachAcceptanceInsightsStoreError(
            "Missing OUTREACH_SUPABASE_URL."
        )

    if not settings.outreach_supabase_secret_key:
        raise OutreachAcceptanceInsightsStoreError(
            "Missing OUTREACH_SUPABASE_SECRET_KEY."
        )

    return create_client(
        settings.outreach_supabase_url,
        settings.outreach_supabase_secret_key,
    )


def _load_all_target_rows(
    *,
    client: Client,
    job_id: str | None = None,
) -> list[dict]:
    """
    Load Outreach Connect targets in pages so All-time analytics
    is not silently capped by PostgREST's default row limit.
    """
    rows: list[dict] = []
    offset = 0

    while True:
        query = (
            client
            .table(
                TARGET_TABLE
            )
            .select(
                (
                    "id,"
                    "job_id,"
                    "prospect_id,"
                    "status,"
                    "assigned_account_id,"
                    "acceptance_status,"
                    "accepted_at,"
                    "outreach_prospects("
                    "connect_status"
                    ")"
                )
            )
        )

        if job_id:
            query = query.eq(
                "job_id",
                job_id,
            )

        response = (
            query
            .range(
                offset,
                offset + PAGE_SIZE - 1,
            )
            .execute()
        )

        page_rows = list(
            response.data
            or []
        )

        rows.extend(
            page_rows
        )

        if len(page_rows) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    return rows


def _load_connect_jobs(
    *,
    client: Client,
) -> list[dict]:
    """
    Return Connect Job IDs/codes for the drawer filter.

    This deliberately comes from the database rather than the
    dashboard's recent-10 list, so old jobs remain filterable.
    """
    rows: list[dict] = []
    offset = 0

    while True:
        response = (
            client
            .table(
                JOB_TABLE
            )
            .select(
                (
                    "id,"
                    "job_code,"
                    "status,"
                    "created_at"
                )
            )
            .eq(
                "job_type",
                "connect",
            )
            .order(
                "created_at",
                desc=True,
            )
            .range(
                offset,
                offset + PAGE_SIZE - 1,
            )
            .execute()
        )

        page_rows = list(
            response.data
            or []
        )

        rows.extend(
            page_rows
        )

        if len(page_rows) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    return [
        {
            "job_id": _safe_text(
                row.get(
                    "id"
                )
            ),
            "job_code": _safe_text(
                row.get(
                    "job_code"
                )
            ),
            "status": _safe_text(
                row.get(
                    "status"
                )
            ),
            "created_at": (
                row.get(
                    "created_at"
                )
            ),
        }
        for row in rows
        if _safe_text(
            row.get(
                "id"
            )
        )
    ]


def _target_is_attributable_connect(
    row: dict,
) -> bool:
    """
    Count only connection requests attributable to the Outreach flow.

    Primary signal:
        outreach_prospects.connect_status == invitation_sent

    Safety fallback:
        acceptance_status == accepted

    The fallback is important because an Acceptance Check can prove
    that a profile is connected even if an older Connect execution
    stored an imperfect result state.

    We intentionally do NOT count:
        pending
        already_connected

    because those relationships may pre-date the current Connect action
    and should not inflate an account's acceptance performance.
    """
    prospect = (
        row.get(
            "outreach_prospects"
        )
        or {}
    )

    connect_status = _safe_text(
        prospect.get(
            "connect_status"
        )
    ).lower()

    acceptance_status = _safe_text(
        row.get(
            "acceptance_status"
        )
    ).lower()

    return (
        connect_status == "invitation_sent"
        or acceptance_status == "accepted"
    )


def get_acceptance_insights(
    *,
    job_id: str | None = None,
    client: Client | None = None,
) -> dict:
    """
    Aggregate Connect -> Acceptance performance by Outreach account.

    Metrics:
        connected
            Number of attributable connection invitations.

        accepted
            Number of those targets whose latest acceptance state
            is accepted.

        acceptance_rate
            accepted / connected

        share_of_total_accepted
            account accepted / all accepted in the selected scope

    Scope:
        job_id is None -> all time
        job_id set     -> one Connect Job
    """
    active_client = (
        client
        if client is not None
        else get_outreach_supabase_client()
    )

    cleaned_job_id = _safe_text(
        job_id
    )

    target_rows = (
        _load_all_target_rows(
            client=active_client,
            job_id=(
                cleaned_job_id
                or None
            ),
        )
    )

    grouped: dict[
        str,
        dict[str, int],
    ] = {}

    for row in target_rows:
        account_id = _safe_text(
            row.get(
                "assigned_account_id"
            )
        )

        if not account_id:
            continue

        if not _target_is_attributable_connect(
            row
        ):
            continue

        account = grouped.setdefault(
            account_id,
            {
                "connected": 0,
                "accepted": 0,
            },
        )

        account[
            "connected"
        ] += 1

        if (
            _safe_text(
                row.get(
                    "acceptance_status"
                )
            ).lower()
            == "accepted"
        ):
            account[
                "accepted"
            ] += 1

    total_connected = sum(
        item[
            "connected"
        ]
        for item in grouped.values()
    )

    total_accepted = sum(
        item[
            "accepted"
        ]
        for item in grouped.values()
    )

    accounts: list[dict] = []

    for account_id, item in grouped.items():
        connected = int(
            item[
                "connected"
            ]
        )

        accepted = int(
            item[
                "accepted"
            ]
        )

        acceptance_rate = (
            accepted / connected
            if connected > 0
            else 0.0
        )

        share = (
            accepted / total_accepted
            if total_accepted > 0
            else 0.0
        )

        accounts.append(
            {
                "account_id": account_id,
                "connected": connected,
                "accepted": accepted,
                "acceptance_rate": (
                    acceptance_rate
                ),
                "share_of_total_accepted": (
                    share
                ),
            }
        )

    accounts.sort(
        key=lambda item: (
            float(
                item[
                    "acceptance_rate"
                ]
            ),
            int(
                item[
                    "accepted"
                ]
            ),
            int(
                item[
                    "connected"
                ]
            ),
        ),
        reverse=True,
    )

    best_performer = (
        accounts[0]
        if accounts
        else None
    )

    overall_rate = (
        total_accepted
        / total_connected
        if total_connected > 0
        else 0.0
    )

    jobs = _load_connect_jobs(
        client=active_client
    )

    selected_job = None

    if cleaned_job_id:
        selected_job = next(
            (
                job
                for job in jobs
                if job[
                    "job_id"
                ] == cleaned_job_id
            ),
            None,
        )

    return {
        "scope": (
            "job"
            if cleaned_job_id
            else "all"
        ),
        "job_id": (
            cleaned_job_id
            or None
        ),
        "selected_job": selected_job,
        "summary": {
            "total_connected": (
                total_connected
            ),
            "total_accepted": (
                total_accepted
            ),
            "overall_rate": (
                overall_rate
            ),
            "best_performer": (
                best_performer
            ),
        },
        "accounts": accounts,
        "jobs": jobs,
        "generated_at": _utc_now(),
    }
