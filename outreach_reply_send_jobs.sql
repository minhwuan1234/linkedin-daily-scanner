create extension if not exists pgcrypto;

create table if not exists public.outreach_reply_send_jobs (
  id uuid primary key default gen_random_uuid(),
  reply_id uuid not null references public.outreach_reply_messages(id) on delete cascade,
  sent_target_id uuid not null references public.outreach_message_targets(id) on delete cascade,
  assigned_account_id text not null,
  user_name text not null,
  linkedin_url text not null,
  message_text text not null,
  status text not null default 'prepared',
  send_attempt_count integer not null default 0,
  prepared_at timestamptz not null default now(),
  queued_at timestamptz null,
  started_at timestamptz null,
  sent_at timestamptz null,
  failed_at timestamptz null,
  last_error text null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint outreach_reply_send_jobs_reply_unique unique (reply_id),
  constraint outreach_reply_send_jobs_status_check
    check (status in ('prepared', 'queued', 'processing', 'sent', 'failed'))
);

create index if not exists outreach_reply_send_jobs_queue_idx
  on public.outreach_reply_send_jobs (assigned_account_id, status, queued_at);

alter table public.outreach_reply_send_jobs enable row level security;

do $$
begin
  alter publication supabase_realtime
    add table public.outreach_reply_send_jobs;
exception
  when duplicate_object then null;
end $$;

comment on table public.outreach_reply_send_jobs is
  'Prepared and queued one-to-one LinkedIn replies sent by the dedicated reply worker.';

notify pgrst, 'reload schema';
