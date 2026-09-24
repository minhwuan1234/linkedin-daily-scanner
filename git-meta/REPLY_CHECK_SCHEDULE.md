# Scheduled LinkedIn reply checks (Mac worker)

The reply-check worker scans the five Outreach accounts sequentially at
**12:00 and 18:00 Asia/Ho_Chi_Minh** every day. It records matched incoming
replies and restores LinkedIn's unread state; it does not send messages.

On the worker Mac, after pulling this repo:

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
