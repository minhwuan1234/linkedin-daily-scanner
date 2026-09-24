-- Apply once in Supabase SQL Editor to show live reply-check activity.
create extension if not exists pgcrypto;

create table if not exists public.outreach_worker_activity (
  id uuid primary key default gen_random_uuid(),
  task_key text not null,
  account_id text not null,
  status text not null check (status in ('running', 'finished')),
  started_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  finished_at timestamptz null
);

create index if not exists outreach_worker_activity_live_idx
  on public.outreach_worker_activity (status, updated_at desc);

alter table public.outreach_worker_activity enable row level security;
notify pgrst, 'reload schema';
