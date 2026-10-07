-- Apply once in Supabase SQL Editor before deploying the all-Unread worker.
-- Unread conversations can exist without a sent Outreach target.
alter table public.outreach_reply_messages
  alter column sent_target_id drop not null;

alter table public.outreach_reply_messages
  add column if not exists thread_url text null;

create unique index if not exists outreach_reply_messages_account_thread_idx
  on public.outreach_reply_messages (assigned_account_id, thread_url)
  where thread_url is not null and thread_url <> '';

alter table public.outreach_reply_send_jobs
  alter column sent_target_id drop not null;

notify pgrst, 'reload schema';
