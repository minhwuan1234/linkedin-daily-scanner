from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from supabase import Client, create_client

from app.settings import load_settings


JOB_TABLE = "outreach_jobs"
PROSPECT_TABLE = "outreach_prospects"
TARGET_TABLE = "outreach_job_targets"

LOCAL_TIMEZONE = ZoneInfo(
    "Asia/Ho_Chi_Minh"
)


class OutreachJobStoreError(
    RuntimeError
):
    pass


@dataclass(frozen=True)
class OutreachJobCreateResult:
    job_id: str
    job_code: str

    input_count: int
    target_count: int
    duplicate_count: int
    invalid_count: int


# =========================================================
# SUPABASE
# =========================================================


def get_outreach_supabase_client() -> Client:
    settings = load_settings()

    if not settings.outreach_supabase_url:
        raise OutreachJobStoreError(
            "Missing OUTREACH_SUPABASE_URL."
        )

    if not settings.outreach_supabase_secret_key:
        raise OutreachJobStoreError(
            "Missing OUTREACH_SUPABASE_SECRET_KEY."
        )

    return create_client(
        settings.outreach_supabase_url,
        settings.outreach_supabase_secret_key,
    )


# =========================================================
# URL NORMALIZATION
# =========================================================


def normalize_linkedin_url(
    url: str,
) -> str:
    """
    Chuẩn hóa LinkedIn profile URL.

    Ví dụ:

    https://www.linkedin.com/in/abc/
    https://linkedin.com/in/abc
    https://www.linkedin.com/in/abc/?trk=xxx

    đều trở thành:

    https://www.linkedin.com/in/abc
    """

    cleaned = str(
        url or ""
    ).strip()

    if not cleaned:
        return ""

    if not cleaned.startswith(
        (
            "http://",
            "https://",
        )
    ):
        cleaned = (
            "https://"
            + cleaned
        )

    try:
        parsed = urlsplit(
            cleaned
        )

    except Exception:
        return ""

    host = (
        parsed.netloc
        .lower()
        .strip()
    )
    
    if (
        host == "linkedin.com"
        or host.endswith(".linkedin.com")
    ):
        host = "www.linkedin.com"
    else:
        return ""

    path = (
        parsed.path
        .strip()
        .rstrip("/")
    )

    if not path.startswith(
        "/in/"
    ):
        return ""

    # Chặn URL bị dính nhiều URL vào nhau
    lowered_path = (
        path.lower()
    )

    if (
        "http://" in lowered_path
        or "https://" in lowered_path
        or "linkedin.com/" in lowered_path[4:]
    ):
        return ""

    # /in/ nhưng không có username
    slug = (
        path[4:]
        .strip("/")
        .strip()
    )

    if not slug:
        return ""

    normalized = urlunsplit(
        (
            "https",
            host,
            path,
            "",
            "",
        )
    )

    return normalized


# =========================================================
# JOB CODE
# =========================================================


def _build_job_code(
    *,
    client: Client,
    input_count: int,
) -> str:
    """
    Format:

    {url_count}-{YYYYMMDD}-{sequence}

    Ví dụ:

    40-20260812-01
    40-20260812-02
    """

    now = datetime.now(
        LOCAL_TIMEZONE
    )

    date_code = now.strftime(
        "%Y%m%d"
    )

    prefix = (
        f"{input_count}-"
        f"{date_code}"
    )

    response = (
        client.table(
            JOB_TABLE
        )
        .select(
            "job_code"
        )
        .like(
            "job_code",
            f"{prefix}-%",
        )
        .execute()
    )

    rows = (
        response.data
        if isinstance(
            response.data,
            list,
        )
        else []
    )

    highest_sequence = 0

    for row in rows:
        job_code = str(
            row.get(
                "job_code",
                "",
            )
            or ""
        ).strip()

        if not job_code:
            continue

        try:
            sequence = int(
                job_code.rsplit(
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

    next_sequence = (
        highest_sequence + 1
    )

    return (
        f"{prefix}-"
        f"{next_sequence:02d}"
    )


# =========================================================
# PROSPECT LOOKUP
# =========================================================


def _find_existing_prospect(
    *,
    client: Client,
    normalized_url: str,
) -> dict | None:
    response = (
        client.table(
            PROSPECT_TABLE
        )
        .select(
            "id,normalized_url"
        )
        .eq(
            "normalized_url",
            normalized_url,
        )
        .limit(
            1
        )
        .execute()
    )

    rows = (
        response.data
        if isinstance(
            response.data,
            list,
        )
        else []
    )

    if not rows:
        return None

    return rows[0]


# =========================================================
# CREATE JOB
# =========================================================


def create_connect_job(
    urls: Iterable[str],
    *,
    client: Client | None = None,
) -> OutreachJobCreateResult:
    """
    Một lần user submit list
    = một Connect Job.

    Flow:

    input
    -> normalize
    -> invalid check
    -> duplicate check
    -> prospect
    -> target
    """

    active_client = (
        client
        if client is not None
        else get_outreach_supabase_client()
    )

    raw_urls = [
        str(url or "").strip()
        for url in urls
        if str(url or "").strip()
    ]

    input_count = len(
        raw_urls
    )

    if input_count == 0:
        raise OutreachJobStoreError(
            "URL list cannot be empty."
        )

    job_code = _build_job_code(
        client=active_client,
        input_count=input_count,
    )

    # -----------------------------------------------------
    # CREATE JOB
    # -----------------------------------------------------

    job_response = (
        active_client.table(
            JOB_TABLE
        )
        .insert(
            {
                "job_type": "connect",
                "job_code": job_code,
                "status": "creating",

                "input_count": input_count,
                "target_count": 0,
                "duplicate_count": 0,
                "invalid_count": 0,

                "processed_count": 0,
                "success_count": 0,
                "failed_count": 0,
            }
        )
        .execute()
    )

    job_rows = (
        job_response.data
        if isinstance(
            job_response.data,
            list,
        )
        else []
    )

    if not job_rows:
        raise OutreachJobStoreError(
            "Could not create outreach job."
        )

    job_id = str(
        job_rows[0]["id"]
    )

    # -----------------------------------------------------
    # COUNTERS
    # -----------------------------------------------------

    target_count = 0
    duplicate_count = 0
    invalid_count = 0

    seen_in_input: set[str] = set()

    # -----------------------------------------------------
    # PROCESS INPUT
    # -----------------------------------------------------

    for raw_url in raw_urls:
        normalized_url = (
            normalize_linkedin_url(
                raw_url
            )
        )

        # ---------------------------------------------
        # INVALID
        # ---------------------------------------------

        if not normalized_url:
            invalid_count += 1
            continue

        # ---------------------------------------------
        # DUPLICATE INSIDE CURRENT INPUT
        # ---------------------------------------------

        if normalized_url in seen_in_input:
            duplicate_count += 1
            continue

        seen_in_input.add(
            normalized_url
        )

        # ---------------------------------------------
        # DUPLICATE FROM PREVIOUS JOBS
        # ---------------------------------------------

        existing = (
            _find_existing_prospect(
                client=active_client,
                normalized_url=normalized_url,
            )
        )

        if existing is not None:
            duplicate_count += 1
            continue

        # ---------------------------------------------
        # CREATE PROSPECT
        # ---------------------------------------------

        prospect_response = (
            active_client.table(
                PROSPECT_TABLE
            )
            .insert(
                {
                    "linkedin_url": raw_url,
                    "normalized_url": normalized_url,
                    "connect_status": "pending",
                    "message_status": "not_started",
                }
            )
            .execute()
        )

        prospect_rows = (
            prospect_response.data
            if isinstance(
                prospect_response.data,
                list,
            )
            else []
        )

        if not prospect_rows:
            raise OutreachJobStoreError(
                "Could not create prospect "
                f"for {normalized_url}"
            )

        prospect_id = str(
            prospect_rows[0]["id"]
        )

        # ---------------------------------------------
        # CREATE TARGET
        # ---------------------------------------------

        (
            active_client.table(
                TARGET_TABLE
            )
            .insert(
                {
                    "job_id": job_id,
                    "prospect_id": prospect_id,
                    "status": "pending",
                    "retry_count": 0,
                }
            )
            .execute()
        )

        target_count += 1

    # -----------------------------------------------------
    # VALIDATE COUNTERS
    # -----------------------------------------------------

    counted_total = (
        target_count
        + duplicate_count
        + invalid_count
    )

    if counted_total != input_count:
        raise OutreachJobStoreError(
            "Outreach job counters are inconsistent. "
            f"input={input_count}, "
            f"target={target_count}, "
            f"duplicate={duplicate_count}, "
            f"invalid={invalid_count}"
        )

    # -----------------------------------------------------
    # UPDATE JOB COUNTERS
    # -----------------------------------------------------

    (
        active_client.table(
            JOB_TABLE
        )
        .update(
            {
                "target_count": target_count,
                "duplicate_count": duplicate_count,
                "invalid_count": invalid_count,
                "status": "pending",
            }
        )
        .eq(
            "id",
            job_id,
        )
        .execute()
    )

    # -----------------------------------------------------
    # RESULT
    # -----------------------------------------------------

    return OutreachJobCreateResult(
        job_id=job_id,
        job_code=job_code,

        input_count=input_count,
        target_count=target_count,
        duplicate_count=duplicate_count,
        invalid_count=invalid_count,
    )
