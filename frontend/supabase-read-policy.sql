alter table public.linkedin_profile_snapshots enable row level security;
grant select on table public.linkedin_profile_snapshots to anon;
drop policy if exists "Dashboard can read profile snapshots" on public.linkedin_profile_snapshots;
create policy "Dashboard can read profile snapshots"
on public.linkedin_profile_snapshots
for select
to anon
using (true);
