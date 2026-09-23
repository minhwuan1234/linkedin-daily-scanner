-- Run once in Supabase SQL Editor before deploying the named Connect batches UI.
alter table public.outreach_jobs
  add column if not exists display_name text;
