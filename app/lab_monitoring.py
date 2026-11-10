"""Read-only monitoring report for AI Agent Lab (protocol app-monitoring-v1, profile-v1).

The Lab calls GET /internal/monitoring?days=N with a bearer token.

Main Job: one Connect batch (a campaign batch). Its sub-jobs follow the outreach flow and are
linked back to the batch they came from:

    Connect batch (outreach_jobs)
      ├─ Gửi lời mời connect   one profile    outreach_job_targets.job_id
      ├─ Kiểm tra chấp nhận    one check run  outreach_acceptance_checks.source_job_id
      ├─ Gửi tin nhắn          one recipient  outreach_message_targets.source_target_id → job target
      └─ Gửi trả lời           one reply      outreach_reply_send_jobs.sent_target_id → message target

The report holds job names, statuses, timestamps and the batch name only: no prospect names,
profile URLs, message text or account identifiers leave this service.
"""

from __future__ import annotations

import json
import os
import platform
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterable

from app.outreach_campaign_identity import connect_batch_label

APP_ID = "outreach"
ROW_LIMIT = 1000
PAGE = 1000
STEP_ROW_LIMIT = 8000
RUN_LIMIT = 5000
HORIZON_DAYS = 61
STARTED_AT = datetime.now(timezone.utc)
_STARTED_MONOTONIC = time.monotonic()

MAIN_JOB = "Connect batch"
STEP_CONNECT = "Gửi lời mời connect"
STEP_ACCEPTANCE = "Kiểm tra chấp nhận"
STEP_MESSAGE = "Gửi tin nhắn"
STEP_REPLY = "Gửi trả lời"
STEPS = (STEP_CONNECT, STEP_ACCEPTANCE, STEP_MESSAGE, STEP_REPLY)


@dataclass(frozen=True)
class JobSource:
    key: str
    table: str
    job: str
    success: str
    failure: str
    start: str
    ends: tuple
    evidence: Callable[[dict], bool]
    columns: str = "*"


def _positive(field: str) -> Callable[[dict], bool]:
    return lambda row: _int(row.get(field)) > 0


# Batch-level tables: aggregated history (Projects tab) and the Connect batch Main Job runs.
JOB_SOURCES = (
    JobSource("connect", "outreach_jobs", MAIN_JOB, "completed", "failed",
              "started_at", ("completed_at",), _positive("processed_count")),
    JobSource("acceptance", "outreach_acceptance_checks", STEP_ACCEPTANCE, "completed", "failed",
              "started_at", ("completed_at",), lambda row: True),
    JobSource("messages", "outreach_message_batches", "Message batch", "completed", "failed",
              "started_at", ("completed_at",), _positive("sent_count")),
    JobSource("reply_send", "outreach_reply_send_jobs", STEP_REPLY, "sent", "failed",
              "started_at", ("sent_at", "failed_at"), lambda row: bool(row.get("sent_at")),
              "id,sent_target_id,status,started_at,sent_at,failed_at,last_error,created_at,updated_at"),
)

INVENTORY_LABELS = {
    "outreach_jobs": "Connect batches",
    "outreach_acceptance_checks": "Kiểm tra chấp nhận",
    "outreach_message_batches": "Batch tin nhắn",
    "outreach_reply_send_jobs": "Gửi trả lời",
    "outreach_account_sessions": "Phiên đăng nhập LinkedIn",
}

# Failures caused by infrastructure rather than by LinkedIn's answer or the input.
TECHNICAL = re.compile(
    r"timeout|timed out|network|connection|econn|socket|playwright|browser|navigation|"
    r"target closed|crash|traceback|exception|supabase|postgrest|http 5\d\d|internal server",
    re.IGNORECASE,
)

RUNNING = ("running", "processing", "sending")


def _int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def _first_time(row: dict, fields: Iterable[str]) -> datetime | None:
    for field in fields:
        parsed = _time(row.get(field))
        if parsed:
            return parsed
    return None


def _end(row: dict, source: JobSource) -> datetime | None:
    return _first_time(row, source.ends)


def job_history(sources: dict, since: datetime | None, truncated: set) -> dict:
    """Terminal jobs (batch tables) whose end falls on/after `since` (None = all saved history)."""
    executed = failed = technical = unclassified = valid = unverified = 0
    latest = None
    complete = not truncated
    for source in JOB_SOURCES:
        rows = sources.get(source.key)
        if rows is None:
            complete = False
            continue
        for row in rows:
            status = str(row.get("status") or "").lower()
            if status not in (source.success, source.failure):
                continue
            end = _end(row, source) or _time(row.get("updated_at"))
            if since and (not end or end < since):
                continue
            executed += 1
            if status == source.failure:
                failed += 1
                if TECHNICAL.search(str(row.get("last_error") or "")):
                    technical += 1
                else:
                    unclassified += 1
            elif source.evidence(row):
                valid += 1
            else:
                unverified += 1
            start, finished = _time(row.get(source.start)), _end(row, source)
            if start and finished and finished >= start and (latest is None or finished > latest[0]):
                latest = (finished, source.job, (finished - start).total_seconds() * 1000)
    return {
        "executed": executed,
        "failed": failed,
        "technicalErrors": technical,
        "unclassifiedFailures": unclassified,
        "validCompletions": valid,
        "unverifiedCompletions": unverified,
        "complete": complete,
        "latestJob": None if latest is None else {
            "job": latest[1], "durationMs": round(latest[2]), "completedAt": latest[0].isoformat(),
        },
    }


# ---------------------------------------------------------------------------------------------
# jobRuns: Connect batch (Main Job) with its sub-jobs
# ---------------------------------------------------------------------------------------------

WORKLOAD_CLASS = "Batch connect"


def batch_workload(row: dict) -> str:
    """'Batch connect · <batch - campaign> (N hồ sơ)'.

    Lab groups statistics by the class before ' · ' (one group, so samples add up quickly) and
    shows the full name in run history."""
    label = connect_batch_label(row.get("batch_name"), row.get("display_name"), row.get("created_at"))
    size = _int(row.get("target_count"))
    return (WORKLOAD_CLASS + " · " + label + (f" ({size} hồ sơ)" if size else ""))[:200]


def _run(job: str, run_id: str, status: str, start: datetime | None, end: datetime | None, *,
         workload: str = "", parent_run_id: str | None = None) -> dict:
    run = {"job": job, "runId": run_id, "workload": workload, "status": status,
           "startedAt": start.isoformat() if start and (end is None or start <= end) else None,
           "endedAt": end.isoformat() if end else None}
    if parent_run_id:
        run["parentRunId"] = parent_run_id
        run["parent"] = MAIN_JOB
    return run


def _outcome(row: dict, success: Iterable[str], failure: Iterable[str], start_field: str,
             end_fields: Iterable[str]) -> tuple[str, datetime | None, datetime | None] | None:
    """(status, start, end) for a finished or running row; None for queued/pending rows."""
    status = str(row.get("status") or "").lower()
    start = _time(row.get(start_field)) if start_field else None
    if status in RUNNING:
        return ("running", start, None) if start else None
    if status in success or status in failure:
        end = _first_time(row, end_fields) or _time(row.get("updated_at"))
        return ("success" if status in success else "failed", start, end) if end else None
    return None


def job_runs(steps: dict, current: datetime, truncated: set, limit: int = RUN_LIMIT) -> dict:
    """app-monitoring-v1 jobRuns over the last 61 days.

    `steps` holds the rows read from Supabase:
      connect     outreach_jobs                 (Main Job runs)
      targets     outreach_job_targets          id, job_id, status, started_at?, completed_at
      acceptance  outreach_acceptance_checks    source_job_id, status, started_at, completed_at
      messages    outreach_message_targets      id, source_target_id, status, started_at, completed_at
      replies     outreach_reply_send_jobs      sent_target_id, status, started_at, sent_at/failed_at
      target_jobs {job target id: connect batch id} for every referenced job target
      message_sources {message target id: job target id} for every referenced message target
    """
    since = current - timedelta(days=HORIZON_DAYS)
    complete = not truncated
    target_jobs = dict(steps.get("target_jobs") or {})
    message_sources = dict(steps.get("message_sources") or {})
    children: list[dict] = []

    def parent_of_target(target_id: Any) -> str | None:
        job_id = target_jobs.get(str(target_id or ""))
        return "connect:" + job_id if job_id else None

    def recent(outcome) -> bool:
        status, start, end = outcome
        moment = end or start
        return bool(moment and moment >= since)

    def add(job: str, run_id: str, outcome, parent: str | None) -> None:
        if outcome and recent(outcome):
            children.append(_run(job, run_id, outcome[0], outcome[1], outcome[2], parent_run_id=parent))

    for row in steps.get("targets") or []:
        target_id = str(row.get("id") or "")
        target_jobs.setdefault(target_id, str(row.get("job_id") or ""))
        outcome = _outcome(row, ("completed",), ("failed",), "started_at", ("completed_at",))
        job_id = str(row.get("job_id") or "")
        add(STEP_CONNECT, "connect-target:" + target_id, outcome, "connect:" + job_id if job_id else None)

    for row in steps.get("acceptance") or []:
        outcome = _outcome(row, ("completed",), ("failed",), "started_at", ("completed_at",))
        job_id = str(row.get("source_job_id") or "")
        add(STEP_ACCEPTANCE, "acceptance:" + str(row.get("id") or ""), outcome, "connect:" + job_id if job_id else None)

    for row in steps.get("messages") or []:
        message_sources.setdefault(str(row.get("id") or ""), str(row.get("source_target_id") or ""))
        outcome = _outcome(row, ("sent",), ("failed",), "started_at", ("completed_at",))
        add(STEP_MESSAGE, "message:" + str(row.get("id") or ""), outcome, parent_of_target(row.get("source_target_id")))

    for row in steps.get("replies") or []:
        outcome = _outcome(row, ("sent",), ("failed",), "started_at", ("sent_at", "failed_at"))
        source = message_sources.get(str(row.get("sent_target_id") or ""))
        add(STEP_REPLY, "reply:" + str(row.get("id") or ""), outcome, parent_of_target(source))

    # Main Job runs: batches in the horizon, plus older batches that still have recent steps,
    # so a late acceptance check or reply is shown inside its batch.
    wanted = {c["parentRunId"] for c in children if c.get("parentRunId")}
    runs: list[dict] = []
    for row in steps.get("connect") or []:
        run_id = "connect:" + str(row.get("id") or "")
        outcome = _outcome(row, ("completed",), ("failed",), "started_at", ("completed_at",))
        if not outcome or not (recent(outcome) or run_id in wanted):
            continue
        runs.append(_run(MAIN_JOB, run_id, outcome[0], outcome[1], outcome[2], workload=batch_workload(row)))
    runs += children

    runs.sort(key=lambda r: r["endedAt"] or r["startedAt"] or "", reverse=True)
    if len(runs) > limit:
        runs, complete = runs[:limit], False
    return {"since": since.isoformat(), "complete": complete, "runs": runs}


# ---------------------------------------------------------------------------------------------
# Profile (Projects tab cards and Lab detection hints)
# ---------------------------------------------------------------------------------------------

def _status_counts(rows: Iterable[dict]) -> list[dict]:
    counts: dict = {}
    for row in rows:
        status = str(row.get("status") or "unknown").lower()
        counts[status] = counts.get(status, 0) + 1
    return [{"status": k, "count": v} for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]


def _in_window(row: dict, since: datetime, *fields: str) -> bool:
    for field in fields:
        parsed = _time(row.get(field))
        if parsed:
            return parsed >= since
    return False


def _sum(rows: Iterable[dict], field: str) -> int:
    return sum(_int(row.get(field)) for row in rows)


def _minutes(values: list) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))] / 60000, 2)


def build_profile(sources: dict, sessions: list | None, workers: dict | None, since: datetime, days: int) -> dict:
    def rows(key: str) -> list:
        return sources.get(key) or []

    def window(key: str, *fields: str) -> list:
        return [r for r in rows(key) if _in_window(r, since, *fields)]

    connect = window("connect", "completed_at", "created_at")
    messages = window("messages", "completed_at", "created_at")
    replies = window("reply_send", "sent_at", "failed_at", "created_at")
    acceptance = window("acceptance", "completed_at", "created_at")
    period = f"{days} ngày gần nhất (UTC)"

    def unknown(key: str) -> bool:
        return sources.get(key) is None

    def value(key: str, number: int) -> int | None:
        return None if unknown(key) else number

    durations = []
    for source in JOB_SOURCES:
        values = []
        for row in window(source.key, *source.ends, "created_at"):
            start, end = _time(row.get(source.start)), _end(row, source)
            if start and end and end >= start and str(row.get("status") or "").lower() == source.success:
                values.append((end - start).total_seconds() * 1000)
        durations.append([source.job, len(values), _minutes(values)])

    connect_sent = _sum(connect, "success_count")
    connect_processed = _sum(connect, "processed_count")
    sections = [
        {
            "id": "funnel",
            "title": "Phễu outreach",
            "description": "Tổng theo job kết thúc trong " + period + ". Số người, không phải số job.",
            "metrics": [
                {"label": "Lời mời connect đã gửi", "value": value("connect", connect_sent)},
                {"label": "Hồ sơ đã xử lý (connect)", "value": value("connect", connect_processed)},
                {"label": "Tỷ lệ gửi connect thành công", "format": "percent",
                 "value": None if unknown("connect") or not connect_processed
                 else round(100 * connect_sent / connect_processed, 1)},
                {"label": "Tin nhắn đã gửi", "value": value("messages", _sum(messages, "sent_count"))},
                {"label": "Tin nhắn lỗi", "value": value("messages", _sum(messages, "failed_count")),
                 "tone": "warning" if _sum(messages, "failed_count") else None},
                {"label": "Trả lời đã gửi", "value": value(
                    "reply_send", sum(1 for r in replies if str(r.get("status")).lower() == "sent"))},
            ],
        },
        {
            "id": "durations",
            "title": "Thời gian chạy theo loại job",
            "description": "P95 từ started_at đến lúc kết thúc, chỉ job thành công trong " + period + ".",
            "table": {"columns": ["Job", "Số job đo được", "P95 (phút)"], "rows": durations},
        },
    ]
    if sessions is not None:
        statuses = {s["status"]: s["count"] for s in _status_counts(sessions)}
        blocked = statuses.get("logged_out", 0) + statuses.get("checkpoint", 0) + statuses.get("failed", 0)
        sections.append({
            "id": "accounts",
            "title": "Tài khoản LinkedIn",
            "description": "Trạng thái phiên đăng nhập hiện tại của các tài khoản chạy outreach.",
            "metrics": [
                {"label": "Đang đăng nhập", "value": statuses.get("logged_in", 0),
                 "tone": "success" if statuses.get("logged_in") else "warning"},
                {"label": "Cần xử lý (đăng xuất / checkpoint / lỗi)", "value": blocked,
                 "tone": "error" if blocked else "success"},
                {"label": "Đang kiểm tra hoặc chờ", "value": statuses.get("checking", 0) + statuses.get("pending", 0)},
                {"label": "Tổng tài khoản", "value": len(sessions)},
            ],
        })
    if workers is not None:
        sections.append({
            "id": "workers",
            "title": "Worker đang chạy",
            "description": "Tác vụ có tín hiệu trong 30 phút gần nhất (reply check: 2 phút).",
            "table": {
                "columns": ["Tác vụ", "Đang chạy"],
                "rows": [[t.get("label") or t.get("key"), t.get("count")] for t in workers.get("tasks", [])],
            },
        })

    return {
        "version": "profile-v1",
        "jobTargets": _job_targets(),
        "inventoryLabels": INVENTORY_LABELS,
        "mainJob": {
            "title": "Outreach LinkedIn theo Connect batch",
            "job": MAIN_JOB,
            "steps": list(STEPS),
            "description": "Một Connect batch của campaign: gửi lời mời, kiểm tra chấp nhận, gửi tin nhắn và trả lời.",
            "metrics": [
                {"label": "Connect batch kết thúc", "value": value("connect", len(connect))},
                {"label": "Lượt kiểm tra chấp nhận", "value": value("acceptance", len(acceptance))},
                {"label": "Batch tin nhắn kết thúc", "value": value("messages", len(messages))},
                {"label": "Lượt gửi trả lời", "value": value("reply_send", len(replies))},
            ],
            "note": "Thời gian Connect batch tính từ lúc bắt đầu đến lúc xử lý xong hồ sơ cuối, gồm cả thời gian chờ quota LinkedIn. "
                    "Kiểm tra chấp nhận, tin nhắn và trả lời diễn ra sau đó nên không cộng vào thời gian batch.",
        },
        "sections": sections,
    }


def _job_targets() -> dict:
    """Optional targets in minutes, e.g. LAB_JOB_TARGETS_MINUTES='{"Connect batch": 120}'."""
    try:
        raw = json.loads(os.getenv("LAB_JOB_TARGETS_MINUTES", "") or "{}")
    except ValueError:
        return {}
    known = {MAIN_JOB, *STEPS}
    return {k: v for k, v in raw.items() if k in known and isinstance(v, (int, float)) and v > 0} if isinstance(raw, dict) else {}


def _rss_bytes() -> int | None:
    try:
        with open("/proc/self/status", encoding="utf8") as status:
            for line in status:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


_SECRETISH = re.compile(r"(eyJ[\w-]{10,}|sb_[\w-]{10,}|[A-Za-z0-9_\-]{32,}|(?:key|token|secret|password)\s*[:=]\s*\S+)", re.IGNORECASE)


def safe_reason(error: BaseException) -> str:
    """Short, secret-free reason: exception type, PostgREST code and message (names only, no data)."""
    code = getattr(error, "code", None)
    message = getattr(error, "message", None) or str(error)
    text = " ".join(str(part) for part in (type(error).__name__ + ":", code, message) if part)
    return _SECRETISH.sub("[ẩn]", text)[:200]


# ---------------------------------------------------------------------------------------------
# Reading Supabase
# ---------------------------------------------------------------------------------------------

def _fetch(client, table: str, columns: str = "*") -> tuple:
    if client is None:
        return None, False, "Không có Supabase client"
    try:
        response = client.table(table).select(columns).order("created_at", desc=True).limit(ROW_LIMIT).execute()
    except Exception as error:
        return None, False, safe_reason(error)
    data = list(response.data or [])
    return data, len(data) >= ROW_LIMIT, None


def _fetch_recent(client, table: str, columns: str, since: datetime) -> tuple:
    """Rows updated since `since`, newest first, in pages, at most STEP_ROW_LIMIT."""
    rows: list = []
    try:
        while len(rows) < STEP_ROW_LIMIT:
            page = (client.table(table).select(columns).gte("updated_at", since.isoformat())
                    .order("updated_at", desc=True).range(len(rows), len(rows) + PAGE - 1).execute())
            data = list(page.data or [])
            rows += data
            if len(data) < PAGE:
                return rows, False, None
    except Exception as error:
        return None, False, safe_reason(error)
    return rows, True, None


def _fetch_by_ids(client, table: str, columns: str, ids: Iterable[str]) -> list:
    wanted = sorted({i for i in ids if i})
    rows: list = []
    for start in range(0, len(wanted), 200):
        rows += list(client.table(table).select(columns).in_("id", wanted[start:start + 200]).execute().data or [])
    return rows


TARGET_COLUMNS = "id,job_id,status,completed_at,updated_at"
MESSAGE_COLUMNS = "id,source_target_id,status,started_at,completed_at,updated_at"
ACCEPTANCE_COLUMNS = "id,source_job_id,status,started_at,completed_at,updated_at"


def read_steps(client, sources: dict, current: datetime, errors: dict, truncated: set) -> dict:
    """Sub-job rows for jobRuns, with only the columns needed (no names, URLs or text)."""
    since = current - timedelta(days=HORIZON_DAYS)
    steps: dict = {"connect": sources.get("connect"), "replies": sources.get("reply_send"),
                   "target_jobs": {}, "message_sources": {}}
    if client is None:
        return steps

    # started_at on job targets exists once outreach_connect_target_started_at.sql is applied.
    targets, cut, error = _fetch_recent(client, "outreach_job_targets", TARGET_COLUMNS + ",started_at", since)
    if error:
        targets, cut, error = _fetch_recent(client, "outreach_job_targets", TARGET_COLUMNS, since)
    for key, table, columns in (("targets", "outreach_job_targets", None),
                                ("messages", "outreach_message_targets", MESSAGE_COLUMNS),
                                ("acceptance", "outreach_acceptance_checks", ACCEPTANCE_COLUMNS)):
        if columns:
            rows, cut, error = _fetch_recent(client, table, columns, since)
        else:
            rows = targets
        steps[key] = rows or []
        if cut:
            truncated.add(table)
        if error:
            errors[table] = error

    try:
        # Replies whose message target is older than the horizon, then message targets whose
        # job target is older: resolve their Connect batch with id lookups (ids only).
        known_messages = {str(r.get("id")) for r in steps["messages"]}
        missing = [str(r.get("sent_target_id") or "") for r in steps["replies"] or []]
        for row in _fetch_by_ids(client, "outreach_message_targets", "id,source_target_id",
                                 [m for m in missing if m not in known_messages]):
            steps["message_sources"][str(row.get("id"))] = str(row.get("source_target_id") or "")
        known_targets = {str(r.get("id")) for r in steps["targets"]}
        sources_needed = [str(r.get("source_target_id") or "") for r in steps["messages"]]
        sources_needed += list(steps["message_sources"].values())
        for row in _fetch_by_ids(client, "outreach_job_targets", "id,job_id",
                                 [t for t in sources_needed if t not in known_targets]):
            steps["target_jobs"][str(row.get("id"))] = str(row.get("job_id") or "")
    except Exception as error:
        errors["liên kết sub-job"] = safe_reason(error)
    return steps


def build_report(client, days: int, *, worker_activity: Callable[[], dict] | None = None,
                 now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
                 client_error: str | None = None) -> dict:
    current = now()
    since = datetime(current.year, current.month, current.day, tzinfo=timezone.utc) - timedelta(days=days - 1)

    db_start = time.monotonic()
    sources: dict = {}
    truncated: set = set()
    errors: dict = {}
    for source in JOB_SOURCES:
        rows, cut, error = _fetch(client, source.table, source.columns)
        sources[source.key] = rows
        if cut:
            truncated.add(source.key)
        if error:
            errors[source.table] = error
    db_ms = round((time.monotonic() - db_start) * 1000 / len(JOB_SOURCES))
    sessions, _, session_error = _fetch(client, "outreach_account_sessions", "status,created_at")
    if session_error:
        errors["outreach_account_sessions"] = session_error
    try:
        workers = worker_activity() if worker_activity and client is not None else None
    except Exception as error:
        workers = None
        errors["outreach_worker_activity"] = safe_reason(error)

    step_truncated: set = set(k for k in truncated if k == "connect")
    steps = read_steps(client, sources, current, errors, step_truncated)

    reachable = [k for k, v in sources.items() if v is not None]
    inventory = {source.table: (None if sources[source.key] is None else _status_counts(sources[source.key]))
                 for source in JOB_SOURCES}
    inventory["outreach_account_sessions"] = None if sessions is None else _status_counts(sessions)

    return {
        "protocol": "app-monitoring-v1",
        "appId": APP_ID,
        "generatedAt": current.isoformat(),
        "window": {"days": days, "start": since.isoformat(), "end": current.isoformat()},
        "runtime": {
            "cpuPercent": None,
            "rssBytes": _rss_bytes(),
            "heapUsedBytes": None,
            "heapTotalBytes": None,
            "uptimeSeconds": round(time.monotonic() - _STARTED_MONOTONIC),
            "startedAt": STARTED_AT.isoformat(),
            "runtimeVersion": "Python " + platform.python_version(),
            "commit": os.getenv("RAILWAY_GIT_COMMIT_SHA") or None,
        },
        "database": {
            "status": "ready" if len(reachable) == len(JOB_SOURCES) else "degraded",
            "responseMs": db_ms if reachable else None,
            "error": client_error or (next(iter(errors.values())) if errors else None),
        },
        "jobRuns": job_runs(steps, current, step_truncated),
        "jobHistory": job_history(sources, since, truncated),
        "jobHistoryAllTime": job_history(sources, None, truncated),
        "inventory": inventory,
        "profile": _with_diagnostics(build_profile(sources, sessions, workers, since, days), client_error, errors),
    }


def _with_diagnostics(profile: dict, client_error: str | None, errors: dict) -> dict:
    """Show why data is missing, first, so 'no data' is never mistaken for zero activity."""
    if not client_error and not errors:
        return profile
    rows = [["Supabase client", client_error]] if client_error else []
    rows += [[table, reason] for table, reason in errors.items()]
    profile["sections"].insert(0, {
        "id": "diagnostics",
        "title": "Chưa đọc được dữ liệu",
        "description": "Các nguồn dưới đây lỗi nên số liệu liên quan hiển thị 'Chưa có dữ liệu' thay vì 0.",
        "table": {"columns": ["Nguồn", "Lý do"], "rows": rows[:12]},
    })
    return profile
