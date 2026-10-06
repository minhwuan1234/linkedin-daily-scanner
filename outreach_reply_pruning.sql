-- Apply once in Supabase SQL Editor before enabling automatic Replies cleanup.
-- A linked Send via worker job must never disappear when its reply is pruned.
alter table public.outreach_reply_send_jobs
  drop constraint if exists outreach_reply_send_jobs_reply_id_fkey;

alter table public.outreach_reply_send_jobs
  add constraint outreach_reply_send_jobs_reply_id_fkey
  foreign key (reply_id)
  references public.outreach_reply_messages(id)
  on delete restrict;

create or replace function public.prune_stale_outreach_replies(
  p_scan_started_at timestamptz
)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  removed_count integer;
begin
  if p_scan_started_at is null or p_scan_started_at > now() then
    raise exception 'A valid scan start time is required';
  end if;

  delete from public.outreach_reply_messages as reply
  where reply.captured_at < p_scan_started_at
    and not exists (
      select 1
      from public.outreach_reply_send_jobs as send_job
      where send_job.reply_id = reply.id
    );

  get diagnostics removed_count = row_count;
  return removed_count;
end;
$$;

revoke all on function public.prune_stale_outreach_replies(timestamptz)
  from public, anon, authenticated;
grant execute on function public.prune_stale_outreach_replies(timestamptz)
  to service_role;

notify pgrst, 'reload schema';
