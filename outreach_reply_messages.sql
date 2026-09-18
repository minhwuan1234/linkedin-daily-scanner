create extension if not exists pgcrypto;

create table if not exists public.outreach_reply_messages (
  id uuid primary key default gen_random_uuid(),
  sent_target_id uuid not null references public.outreach_message_targets(id) on delete cascade,
  prospect_id uuid null,
  assigned_account_id text not null,
  user_name text not null,
  linkedin_url text not null,
  message_text text not null,
  linkedin_message_time text null,
  conversation_messages jsonb not null default '[]'::jsonb,
  match_reason text null,
  match_similarity double precision not null default 0,
  message_fingerprint text not null unique,
  captured_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  constraint outreach_reply_messages_similarity_check
    check (match_similarity >= 0 and match_similarity <= 1)
);

create index if not exists outreach_reply_messages_captured_at_idx
  on public.outreach_reply_messages (captured_at desc);

create index if not exists outreach_reply_messages_target_idx
  on public.outreach_reply_messages (sent_target_id);

delete from public.outreach_reply_messages older
using public.outreach_reply_messages newer
where older.sent_target_id = newer.sent_target_id
  and (
    older.captured_at < newer.captured_at
    or (
      older.captured_at = newer.captured_at
      and older.id::text < newer.id::text
    )
  );

create unique index if not exists outreach_reply_messages_sent_target_unique_idx
  on public.outreach_reply_messages (sent_target_id);

create index if not exists outreach_reply_messages_account_idx
  on public.outreach_reply_messages (assigned_account_id, captured_at desc);

alter table public.outreach_reply_messages enable row level security;

alter table public.outreach_reply_messages
  add column if not exists conversation_messages jsonb
  not null default '[]'::jsonb;

comment on table public.outreach_reply_messages is
  'Replies captured by the dedicated LinkedIn Outreach reply-check worker.';
