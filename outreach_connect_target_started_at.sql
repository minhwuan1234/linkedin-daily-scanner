-- Start time of each connect attempt, used by AI Agent Lab (Performance → Status) to time the
-- "Gửi lời mời connect" sub-job. Optional: without it the worker and the report keep working,
-- and connect attempts count toward success rates but not durations.
alter table public.outreach_job_targets
  add column if not exists started_at timestamptz;
