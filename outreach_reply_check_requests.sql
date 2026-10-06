-- Apply once in Supabase SQL Editor to enable manual reply scans from the dashboard.
create extension if not exists pgcrypto;

create table if not exists public.outreach_reply_check_requests (
  id uuid primary key default gen_random_uuid(),
  status text not null default 'queued'
    check (status in ('queued', 'running', 'completed', 'failed')),
  requested_at timestamptz not null default now(),
  started_at timestamptz null,
  finished_at timestamptz null,
  error text null
);

create index if not exists outreach_reply_check_requests_queue_idx
  on public.outreach_reply_check_requests (status, requested_at);

alter table public.outreach_reply_check_requests enable row level security;
notify pgrst, 'reload schema';
