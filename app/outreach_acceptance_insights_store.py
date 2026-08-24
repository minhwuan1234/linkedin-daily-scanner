from __future__ import annotations

from datetime import datetime, timedelta, timezone

from supabase import Client, create_client

from app.settings import load_settings


TARGET_TABLE = "outreach_job_targets"
JOB_TABLE = "outreach_jobs"

PAGE_SIZE = 1000

LOCAL_TIMEZONE = timezone(
    timedelta(hours=7)
)


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


def _parse_datetime(
    value,
) -> datetime | None:
    text = _safe_text(
        value
    )

    if not text:
        return None

    try:
        return datetime.fromisoformat(
            text.replace(
                "Z",
                "+00:00",
            )
        )

    except ValueError:
        return None


def _normalise_week_start(
    value,
) -> str:
    text = _safe_text(
        value
    )

    if not text:
        return ""

    try:
        parsed = datetime.strptime(
            text,
            "%Y-%m-%d",
        ).date()

    except ValueError as exc:
        raise OutreachAcceptanceInsightsStoreError(
            "week_start must use YYYY-MM-DD."
        ) from exc

    monday = (
        parsed
        - timedelta(
            days=parsed.weekday()
        )
    )

    return monday.isoformat()


def _week_bounds(
    week_start: str,
) -> tuple[str, str]:
    monday = datetime.strptime(
        week_start,
        "%Y-%m-%d",
    ).date()

    next_monday = (
        monday
        + timedelta(days=7)
    )

    start = datetime(
        monday.year,
        monday.month,
        monday.day,
        tzinfo=LOCAL_TIMEZONE,
    )

    end = datetime(
        next_monday.year,
        next_monday.month,
        next_monday.day,
        tzinfo=LOCAL_TIMEZONE,
    )

    return (
        start.astimezone(
            timezone.utc
        ).isoformat(),
        end.astimezone(
            timezone.utc
        ).isoformat(),
    )


def _week_start_for_datetime(
    value,
) -> str:
    parsed = _parse_datetime(
        value
    )

    if parsed is None:
        return ""

    local_date = parsed.astimezone(
        LOCAL_TIMEZONE
    ).date()

    monday = (
        local_date
        - timedelta(
            days=local_date.weekday()
        )
    )

    return monday.isoformat()


def _format_week_label(
    week_start: str,
) -> str:
    monday = datetime.strptime(
        week_start,
        "%Y-%m-%d",
    ).date()

    sunday = (
        monday
        + timedelta(days=6)
    )

    return (
        f"{monday.strftime('%d/%m/%Y')}"
        " - "
        f"{sunday.strftime('%d/%m/%Y')}"
    )


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
    week_start: str | None = None,
) -> list[dict]:
    """
    Load Outreach Connect targets in pages.

    Weekly scope is based on outreach_job_targets.completed_at.

    That timestamp belongs to the specific Connect Job target and is set
    when that target finishes its Connect execution. Acceptance scans run
    later and do not modify this timestamp, so an acceptance discovered
    this week remains attributed to the week its invitation was sent.
    """
    rows: list[dict] = []
    offset = 0

    cleaned_week_start = (
        _normalise_week_start(
            week_start
        )
        if week_start
        else ""
    )

    week_bounds = (
        _week_bounds(
            cleaned_week_start
        )
        if cleaned_week_start
        else None
    )

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
                    "created_at,"
                    "completed_at,"
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

        # Weekly attribution is based on THIS job target's own
        # Connect execution time. target.completed_at is written when the
        # Connect target finishes processing, so later Acceptance scans
        # cannot move it into a newer week.
        if week_bounds:
            query = (
                query
                .gte(
                    "completed_at",
                    week_bounds[0],
                )
                .lt(
                    "completed_at",
                    week_bounds[1],
                )
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
    Return Connect Job IDs/codes for filters.

    Job created_at is also used to build the available week list.
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


def _build_week_options(
    jobs: list[dict],
) -> list[dict]:
    week_starts = {
        _week_start_for_datetime(
            job.get(
                "created_at"
            )
        )
        for job in jobs
    }

    week_starts.discard(
        ""
    )

    current_week = _week_start_for_datetime(
        datetime.now(
            LOCAL_TIMEZONE
        ).isoformat()
    )

    if current_week:
        week_starts.add(
            current_week
        )

    result: list[dict] = []

    for week_start in sorted(
        week_starts,
        reverse=True,
    ):
        monday = datetime.strptime(
            week_start,
            "%Y-%m-%d",
        ).date()

        result.append(
            {
                "week_start": week_start,
                "week_end": (
                    monday
                    + timedelta(days=6)
                ).isoformat(),
                "label": _format_week_label(
                    week_start
                ),
            }
        )

    return result


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
    week_start: str | None = None,
    client: Client | None = None,
) -> dict:
    """
    Aggregate Connect -> Acceptance performance by Outreach account.

    Scope:
        no job_id / no week_start -> all time
        job_id                    -> one Connect Job
        week_start=YYYY-MM-DD     -> Monday-Sunday week

    Weekly grouping is based on outreach_job_targets.completed_at,
    i.e. when the specific Connect target was processed/sent. It never
    uses the later Acceptance Check timestamp and never uses the prospect's
    mutable latest-connect timestamp.
    """
    active_client = (
        client
        if client is not None
        else get_outreach_supabase_client()
    )

    cleaned_job_id = _safe_text(
        job_id
    )

    cleaned_week_start = (
        _normalise_week_start(
            week_start
        )
        if week_start
        else ""
    )

    if (
        cleaned_job_id
        and cleaned_week_start
    ):
        raise OutreachAcceptanceInsightsStoreError(
            "Use either job_id or week_start, not both."
        )

    jobs = _load_connect_jobs(
        client=active_client
    )

    weeks = _build_week_options(
        jobs
    )

    target_rows = _load_all_target_rows(
        client=active_client,
        job_id=(
            cleaned_job_id
            or None
        ),
        week_start=(
            cleaned_week_start
            or None
        ),
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

    selected_week = None

    if cleaned_week_start:
        selected_week = next(
            (
                week
                for week in weeks
                if week[
                    "week_start"
                ] == cleaned_week_start
            ),
            {
                "week_start": (
                    cleaned_week_start
                ),
                "week_end": (
                    datetime.strptime(
                        cleaned_week_start,
                        "%Y-%m-%d",
                    ).date()
                    + timedelta(days=6)
                ).isoformat(),
                "label": _format_week_label(
                    cleaned_week_start
                ),
            },
        )

    scope = "all"

    if cleaned_job_id:
        scope = "job"

    elif cleaned_week_start:
        scope = "week"

    return {
        "scope": scope,
        "job_id": (
            cleaned_job_id
            or None
        ),
        "week_start": (
            cleaned_week_start
            or None
        ),
        "selected_job": selected_job,
        "selected_week": selected_week,
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
        "weeks": weeks,
        "generated_at": _utc_now(),
    }

