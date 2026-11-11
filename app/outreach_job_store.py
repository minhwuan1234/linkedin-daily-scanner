from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from supabase import Client, create_client

from app.outreach_campaign_identity import canonical_campaign_name
from app.outreach_connect_input import prepare_connect_entries
from app.settings import load_settings


JOB_TABLE = "outreach_jobs"
PROSPECT_TABLE = "outreach_prospects"
TARGET_TABLE = "outreach_job_targets"
MAX_CONNECT_URLS = 150
# URLs per lookup query; keeps the GET query string well under proxy limits.
PROSPECT_LOOKUP_CHUNK = 50

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
    batch_name: str

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


# @layer database
# @feature connect
def list_connect_campaigns(*, client: Client | None = None) -> list[str]:
    """Existing campaign names, backed by Connect jobs (no migration needed)."""
    active_client = client if client is not None else get_outreach_supabase_client()
    names: dict[str, str] = {}
    offset = 0
    page_size = 1000
    while True:
        response = (
            active_client.table(JOB_TABLE)
            .select("display_name")
            .eq("job_type", "connect")
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = response.data if isinstance(response.data, list) else []
        for row in rows:
            name = canonical_campaign_name(row.get("display_name"))
            if name:
                names.setdefault(name.casefold(), name)
        if len(rows) < page_size:
            break
        offset += page_size
    return sorted(names.values(), key=str.casefold)


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


def _find_existing_prospect_urls(
    *,
    client: Client,
    normalized_urls: list[str],
) -> set[str]:
    """Normalized URLs that already have a prospect, in a few queries for the whole input."""
    found: set[str] = set()
    for offset in range(0, len(normalized_urls), PROSPECT_LOOKUP_CHUNK):
        chunk = normalized_urls[offset:offset + PROSPECT_LOOKUP_CHUNK]
        response = (
            client.table(PROSPECT_TABLE)
            .select("normalized_url")
            .in_("normalized_url", chunk)
            .execute()
        )
        rows = response.data if isinstance(response.data, list) else []
        found.update(str(row.get("normalized_url")) for row in rows)
    return found


# =========================================================
# CREATE JOB
# =========================================================


def create_connect_job(
    urls: Iterable[str],
    *,
    display_name: str = "",
    batch_name: str = "",
    company_names: list[str] | None = None,
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

    try:
        entries = prepare_connect_entries(urls, company_names)
    except ValueError as exc:
        raise OutreachJobStoreError(str(exc)) from exc

    input_count = len(
        entries
    )

    if input_count == 0:
        raise OutreachJobStoreError(
            "URL list cannot be empty."
        )

    if input_count > MAX_CONNECT_URLS:
        raise OutreachJobStoreError(
            f"Maximum {MAX_CONNECT_URLS} LinkedIn profile URLs per Connect job."
        )

    if company_names is not None:
        # Fail before creating a job if the company column is not deployed yet.
        try:
            active_client.table(PROSPECT_TABLE).select("company_name").limit(1).execute()
        except Exception as exc:
            raise OutreachJobStoreError(
                "Could not access company-name storage. Apply "
                "outreach_connect_company_names.sql and try again."
            ) from exc

    job_code = _build_job_code(
        client=active_client,
        input_count=input_count,
    )
    effective_batch_name = " ".join(str(batch_name or "").split()) or datetime.now(
        LOCAL_TIMEZONE
    ).strftime("%d/%m/%Y")

    # -----------------------------------------------------
    # CREATE JOB
    # -----------------------------------------------------

    job_data = {
        "job_type": "connect",
        "job_code": job_code,
        "batch_name": effective_batch_name,
        "status": "creating",
        "input_count": input_count,
        "target_count": 0,
        "duplicate_count": 0,
        "invalid_count": 0,
        "processed_count": 0,
        "success_count": 0,
        "failed_count": 0,
    }
    if display_name:
        job_data["display_name"] = display_name

    job_response = (
        active_client.table(
            JOB_TABLE
        )
        .insert(job_data)
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
    # PROCESS INPUT
    # -----------------------------------------------------
    # A few batched writes instead of three round trips per URL: 100 URLs used to take
    # ~300 sequential Supabase calls (~45 s), which the user waited on after Start Connect.

    duplicate_count = 0
    invalid_count = 0

    seen_in_input: set[str] = set()
    candidates: list[tuple[str, str, str]] = []

    for raw_url, company_name in entries:
        normalized_url = normalize_linkedin_url(raw_url)

        if not normalized_url:
            invalid_count += 1
            continue

        if normalized_url in seen_in_input:
            duplicate_count += 1
            continue

        seen_in_input.add(normalized_url)
        candidates.append((raw_url, normalized_url, company_name))

    # Duplicates from previous jobs.
    existing_urls = _find_existing_prospect_urls(
        client=active_client,
        normalized_urls=[normalized for _, normalized, _ in candidates],
    )
    new_entries = [entry for entry in candidates if entry[1] not in existing_urls]
    duplicate_count += len(candidates) - len(new_entries)

    # Prospects and targets.
    prospect_rows: list[dict] = []
    for raw_url, normalized_url, company_name in new_entries:
        prospect_data = {
            "linkedin_url": raw_url,
            "normalized_url": normalized_url,
            "connect_status": "pending",
            "message_status": "not_started",
        }
        if company_name:
            prospect_data["company_name"] = company_name
        prospect_rows.append(prospect_data)

    prospect_ids: list[str] = []
    if prospect_rows:
        prospect_response = (
            active_client.table(PROSPECT_TABLE)
            .insert(prospect_rows)
            .execute()
        )
        inserted = prospect_response.data if isinstance(prospect_response.data, list) else []
        ids_by_url = {
            str(row.get("normalized_url")): str(row["id"])
            for row in inserted
            if row.get("id")
        }
        missing = [row["normalized_url"] for row in prospect_rows if row["normalized_url"] not in ids_by_url]
        if missing:
            raise OutreachJobStoreError(
                "Could not create prospect "
                f"for {missing[0]}"
            )
        prospect_ids = [ids_by_url[row["normalized_url"]] for row in prospect_rows]

        try:
            (
                active_client.table(TARGET_TABLE)
                .insert([
                    {
                        "job_id": job_id,
                        "prospect_id": prospect_id,
                        "status": "pending",
                        "retry_count": 0,
                    }
                    for prospect_id in prospect_ids
                ])
                .execute()
            )
        except Exception:
            # Without targets these prospects would block the same URLs as "duplicates"
            # in every later job, so remove them before reporting the failure.
            try:
                active_client.table(PROSPECT_TABLE).delete().in_("id", prospect_ids).execute()
            except Exception:
                pass
            raise

    target_count = len(prospect_ids)

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
        batch_name=effective_batch_name,

        input_count=input_count,
        target_count=target_count,
        duplicate_count=duplicate_count,
        invalid_count=invalid_count,
    )
