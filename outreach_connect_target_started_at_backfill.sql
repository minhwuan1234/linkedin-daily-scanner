-- One-time backfill of started_at for connect attempts made before the worker recorded it.
--
-- The connect worker handles one profile at a time per account and waits a fixed
-- PROFILE_DELAY_SECONDS = 2.5 s between profiles (outreach_connect_worker.py). So inside one
-- Connect batch (job_id) and one account (assigned_account_id), an attempt started about 2.5 s
-- after the previous attempt completed (within about a second: the time to save the result).
--
-- Filled only when:
--   * started_at is empty (real start times are never overwritten),
--   * the attempt has a previous attempt in the same batch and account,
--   * the gap to that previous attempt is 3 s to 3 min (a longer gap may hide a quota wait,
--     an account switch or a pause, so the start is unknown and stays empty).
-- The first attempt of each batch/account turn stays empty and shows "–" in AI Agent Lab.
--
-- Safe to run again: it only fills rows that are still empty.
-- Requires outreach_connect_target_started_at.sql (the started_at column).

begin;

with t as (
  select id,
         started_at,
         completed_at,
         lag(completed_at) over (partition by job_id, assigned_account_id order by completed_at) as previous_done
  from outreach_job_targets
  where completed_at is not null
)
update outreach_job_targets o
set started_at = t.previous_done + interval '2.5 seconds'
from t
where o.id = t.id
  and t.started_at is null
  and t.previous_done is not null
  and t.completed_at - t.previous_done between interval '3 seconds' and interval '3 minutes';

-- Result: how many attempts still have no start time.
select count(*) filter (where started_at is null) as still_missing_start,
       count(*) filter (where started_at is not null) as with_start
from outreach_job_targets
where completed_at is not null;

commit;
