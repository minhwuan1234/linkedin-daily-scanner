# Scheduled LinkedIn reply checks (Mac worker)

The reply-check worker scans the five Outreach accounts sequentially at
**12:00 and 18:00 Asia/Ho_Chi_Minh** every day. It records matched incoming
replies and restores LinkedIn's unread state; it does not send messages.
The Replies inbox reads those saved conversations and checks for new scan data
every 30 seconds while the tab is open, updating the selected chat when it changes.
For unread people whose display name differs from their LinkedIn URL slug, the
worker opens the thread and verifies the profile link or a unique message sent
by the active Outreach account. It does not treat a fuzzy name as proof. If the
Unread list has not settled or visible rows cannot be read, the scan fails
without pruning stored replies.

On the worker Mac, after pulling this repo:

First apply `outreach_reply_pruning.sql` once in the Supabase SQL Editor. The
database function removes replies absent from a successful five-account Unread
scan, while preserving replies linked to any Send via worker job. Those
preserved older replies are hidden from the live Replies inbox but remain in
the database with their jobs. The foreign key is changed from CASCADE to
RESTRICT so a concurrent send job cannot be deleted by cleanup. Without this
SQL migration, the scan will report a cleanup error instead of silently
claiming completion.

```bash
cd /path/to/linkedin-daily-scanner
.venv/bin/python3 -m playwright install chromium
zsh git-meta/reply_check_schedule_service.sh install
zsh git-meta/reply_check_schedule_service.sh status
```

The LaunchAgent starts at login, prevents idle system sleep while waiting, and restarts
if the scheduler exits unexpectedly. The Python scheduler uses Vietnam time
regardless of the Mac's system timezone. It does not run a missed slot after
the Mac has been off; the next scheduled slot runs normally.

Logs are in `logs/reply-check.out.log` and `logs/reply-check.err.log`. To stop
the scheduled service, run:

```bash
zsh git-meta/reply_check_schedule_service.sh uninstall
```

For a one-off scan of all five accounts:

```bash
.venv/bin/python3 -u outreach_reply_check_worker.py --all-accounts
```

Do not run other workers against the same persistent LinkedIn browser profile
at the same time as a reply scan.
