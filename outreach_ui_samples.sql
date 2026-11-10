-- Browser timings of the dashboard's "Start Connect" action, reported to AI Agent Lab as
-- Tốc độ phản hồi (responseTime) and Độ nhạy thao tác (clickLatency). Only the metric name, the
-- duration and the time are stored. Optional: without it samples are kept in memory only and
-- are lost on each redeploy.
create table if not exists public.outreach_ui_samples (
  id bigint generated always as identity primary key,
  metric text not null check (metric in ('responseTime', 'clickLatency')),
  ms numeric not null check (ms >= 0 and ms <= 600000),
  created_at timestamptz not null default now()
);

create index if not exists outreach_ui_samples_created_at_idx
  on public.outreach_ui_samples (created_at desc);

alter table public.outreach_ui_samples enable row level security;
