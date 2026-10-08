"""Read-only campaign cohorts across Connect, Messages, and Replies."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from supabase import Client

from app.outreach_campaign_identity import campaign_id_for_name, canonical_campaign_name
from app.outreach_dashboard_store import get_outreach_client


WINDOW_DAYS = {"1d": 1, "7d": 7, "30d": 30, "all": None}
REPLY_COUNT_START = datetime(2026, 10, 12, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
PAGE_SIZE = 500
IN_CHUNK_SIZE = 100


def _text(value) -> str:
    return str(value or "").strip()


def _chunks(values: list[str]):
    for index in range(0, len(values), IN_CHUNK_SIZE):
        yield values[index:index + IN_CHUNK_SIZE]


def _fetch_pages(query) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        response = query.range(offset, offset + PAGE_SIZE - 1).execute()
        page = list(response.data or [])
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        offset += PAGE_SIZE


def _fetch_related(client: Client, table: str, fields: str,
                   foreign_key: str, ids: list[str], status: str = "",
                   created_since: str = "") -> list[dict]:
    rows: list[dict] = []
    for chunk in _chunks(ids):
        query = client.table(table).select(fields).in_(foreign_key, chunk).order("id")
        if status:
            query = query.eq("status", status)
        if created_since:
            query = query.gte("created_at", created_since)
        rows.extend(_fetch_pages(query))
    return rows


def aggregate_campaign_performance(jobs: list[dict], connect_targets: list[dict],
                                   sent_targets: list[dict], replies: list[dict]) -> list[dict]:
    """Count distinct prospects; only first-recorded replies after the reset qualify."""
    campaigns: dict[str, dict] = {}
    batch_by_id: dict[str, dict] = {}
    campaign_by_batch: dict[str, dict] = {}
    for job in sorted(jobs, key=lambda item: _text(item.get("created_at")), reverse=True):
        batch_id = _text(job.get("id"))
        if not batch_id:
            continue
        name = canonical_campaign_name(job.get("display_name"))
        campaign_id = campaign_id_for_name(name, connect_batch_id=batch_id)
        campaign = campaigns.setdefault(campaign_id, {
            "campaign_id": campaign_id,
            "campaign_name": name or "Unnamed campaign",
            "batches": [],
            "accounts": [], "_accounts": {},
            "_added": set(), "_messaged": set(), "_replied": set(),
        })
        batch = {
            "batch_id": batch_id,
            "batch_code": _text(job.get("job_code")) or batch_id,
            "created_at": job.get("created_at"),
            "_added": set(), "_messaged": set(), "_replied": set(),
        }
        campaign["batches"].append(batch)
        batch_by_id[batch_id] = batch
        campaign_by_batch[batch_id] = campaign

    def account_bucket(batch_id: str, account_id: str) -> dict:
        campaign = campaign_by_batch[batch_id]
        account_key = account_id or "unassigned"
        return campaign["_accounts"].setdefault(account_key, {
            "account_id": account_key,
            "_added": set(), "_messaged": set(), "_replied": set(),
        })

    connect_by_target: dict[str, tuple[str, str, str]] = {}
    for target in connect_targets:
        target_id = _text(target.get("id"))
        batch_id = _text(target.get("job_id"))
        batch = batch_by_id.get(batch_id)
        if not target_id or not batch:
            continue
        person_id = _text(target.get("prospect_id")) or target_id
        account_id = _text(target.get("assigned_account_id"))
        connect_by_target[target_id] = (batch_id, person_id, account_id)
        batch["_added"].add(person_id)
        account_bucket(batch_id, account_id)["_added"].add(person_id)

    sent_by_id: dict[str, tuple[str, str, str]] = {}
    for target in sent_targets:
        source = connect_by_target.get(_text(target.get("source_target_id")))
        sent_id = _text(target.get("id"))
        if not source or not sent_id:
            continue
        batch_id, person_id, connect_account_id = source
        account_id = _text(target.get("assigned_account_id")) or connect_account_id
        batch_by_id[batch_id]["_messaged"].add(person_id)
        account_bucket(batch_id, account_id)["_messaged"].add(person_id)
        sent_by_id[sent_id] = (batch_id, person_id, account_id)

    for reply in replies:
        try:
            first_recorded = datetime.fromisoformat(
                _text(reply.get("created_at")).replace("Z", "+00:00")
            )
            if first_recorded.tzinfo is None or first_recorded < REPLY_COUNT_START:
                continue
        except ValueError:
            continue
        source = sent_by_id.get(_text(reply.get("sent_target_id")))
        if source:
            batch_id, person_id, account_id = source
            batch_by_id[batch_id]["_replied"].add(person_id)
            account_bucket(batch_id, account_id)["_replied"].add(person_id)

    results: list[dict] = []
    for campaign in campaigns.values():
        for batch in campaign["batches"]:
            for metric in ("added", "messaged", "replied"):
                campaign[f"_{metric}"].update(batch[f"_{metric}"])
                batch[metric if metric != "replied" else "replies"] = len(batch.pop(f"_{metric}"))
            batch["reply_rate"] = round(100 * batch["replies"] / batch["messaged"], 1) if batch["messaged"] else 0.0
        for metric in ("added", "messaged", "replied"):
            campaign[metric if metric != "replied" else "replies"] = len(campaign.pop(f"_{metric}"))
        campaign["reply_rate"] = round(100 * campaign["replies"] / campaign["messaged"], 1) if campaign["messaged"] else 0.0
        for account in campaign.pop("_accounts").values():
            for metric in ("added", "messaged", "replied"):
                account[metric if metric != "replied" else "replies"] = len(account.pop(f"_{metric}"))
            account["reply_rate"] = round(100 * account["replies"] / account["messaged"], 1) if account["messaged"] else 0.0
            campaign["accounts"].append(account)
        campaign["accounts"].sort(key=lambda account: (-account["messaged"], account["account_id"]))
        campaign["batches"].sort(key=lambda batch: _text(batch["created_at"]), reverse=True)
        campaign["batch_ids"] = [batch["batch_code"] for batch in campaign["batches"]]
        results.append(campaign)
    return sorted(results, key=lambda campaign: _text(campaign["batches"][0]["created_at"]), reverse=True)


def get_campaign_performance(window: str = "all", *, client: Client | None = None) -> list[dict]:
    if window not in WINDOW_DAYS:
        raise ValueError("Unsupported campaign timeframe.")
    active_client = client or get_outreach_client()
    query = active_client.table("outreach_jobs").select(
        "id,job_code,display_name,created_at"
    ).eq("job_type", "connect").order("id")
    days = WINDOW_DAYS[window]
    if days is not None:
        cutoff = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")) - timedelta(days=days)
        query = query.gte("created_at", cutoff.isoformat())
    jobs = _fetch_pages(query)
    job_ids = [_text(job.get("id")) for job in jobs if _text(job.get("id"))]
    if not job_ids:
        return []
    connect_targets = _fetch_related(
        active_client, "outreach_job_targets", "id,job_id,prospect_id,assigned_account_id", "job_id", job_ids
    )
    source_ids = [_text(row.get("id")) for row in connect_targets if _text(row.get("id"))]
    sent_targets = _fetch_related(
        active_client, "outreach_message_targets", "id,source_target_id,assigned_account_id", "source_target_id", source_ids,
        status="sent",
    )
    sent_ids = [_text(row.get("id")) for row in sent_targets if _text(row.get("id"))]
    replies = _fetch_related(
        active_client, "outreach_reply_messages", "id,sent_target_id,created_at", "sent_target_id", sent_ids,
        created_since=REPLY_COUNT_START.isoformat(),
    )
    return aggregate_campaign_performance(jobs, connect_targets, sent_targets, replies)
