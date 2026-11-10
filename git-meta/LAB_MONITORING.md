# AI Agent Lab monitoring

`GET /internal/monitoring?days=1..30` returns an `app-monitoring-v1` report for AI Agent Lab
(Performance → Status). It is read-only and disabled (404) until `LAB_MONITORING_TOKEN` is set.

## Setup

1. Railway → this service → Variables: `LAB_MONITORING_TOKEN` = a random string of at least 32
   characters. Redeploy.
2. Supabase (outreach project) → SQL editor: run `outreach_connect_target_started_at.sql`
   (optional; it times each connect attempt). The connect worker runs on the worker Mac, not
   on Railway: pull the latest code there and restart the connect worker once. Afterwards,
   if the SQL is applied later, the worker picks the column up within 10 minutes without a
   restart. Only connect attempts made from then on have a start time.
3. AI Agent Lab → Settings → Monitoring → "+ Kết nối tool": the service URL and the same token.
   Lab detects the Main Job, sub-jobs and targets from the report.

## What the report contains

Main Job **Connect batch** (one campaign batch, `outreach_jobs`). Its sub-jobs, in order, are
linked back to the batch they came from:

| Sub-job | One run is | Source | Linked by |
| --- | --- | --- | --- |
| Gửi lời mời connect | one profile | `outreach_job_targets` | `job_id` |
| Kiểm tra chấp nhận | one check run | `outreach_acceptance_checks` | `source_job_id` |
| Gửi tin nhắn | one recipient | `outreach_message_targets` | `source_target_id` → job target |
| Gửi trả lời | one reply | `outreach_reply_send_jobs` | `sent_target_id` → message target |

- Workload: `Batch connect · <batch - campaign> (N hồ sơ)`. Lab groups statistics by the part
  before ` · ` and shows the full name in run history.
- Connect batch time runs from `started_at` to `completed_at`, quota waits included.
  Acceptance checks, messages and replies happen days later, so they are shown inside the
  batch but never added to its time.
- Before the SQL above is applied, connect attempts have no start time: they count toward
  success rates but not durations.
- Runs from the last 61 days (at most 5,000). An older batch is included when a recent step
  belongs to it.
- No prospect names, profile URLs, message text or account identifiers are sent; sub-job
  tables are read with only ids, statuses and timestamps.
- Optional targets: `LAB_JOB_TARGETS_MINUTES='{"Connect batch": 240}'` (minutes, per job).
