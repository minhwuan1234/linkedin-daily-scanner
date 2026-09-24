-- Enable immediate queued-batch notifications for outreach_message_worker.py.
-- The worker still checks once every five minutes if Realtime is unavailable.
do $$
begin
  alter publication supabase_realtime
    add table public.outreach_message_batches;
exception
  when duplicate_object then null;
end $$;
