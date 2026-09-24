#!/bin/zsh
set -euo pipefail

LABEL="com.linkedin.daily-scanner.reply-check"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$PROJECT_DIR/logs"
PYTHON_BIN="$PROJECT_DIR/.venv/bin/python3"
WORKER_FILE="$PROJECT_DIR/outreach_reply_check_worker.py"
DOMAIN="gui/$(id -u)"

case "${1:-install}" in
  install)
    if [[ ! -x "$PYTHON_BIN" ]]; then
      echo "Missing virtualenv Python: $PYTHON_BIN" >&2
      exit 1
    fi
    if [[ ! -f "$WORKER_FILE" ]]; then
      echo "Missing reply-check worker: $WORKER_FILE" >&2
      exit 1
    fi
    if [[ ! -f "$PROJECT_DIR/.env" ]]; then
      echo "Missing environment file: $PROJECT_DIR/.env" >&2
      exit 1
    fi

    mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"
    "$PYTHON_BIN" - "$PLIST_PATH" "$PROJECT_DIR" "$PYTHON_BIN" "$WORKER_FILE" "$LOG_DIR" "$HOME" <<'PY'
import plistlib
import sys

plist_path, project_dir, python_bin, worker_file, log_dir, home = sys.argv[1:]
payload = {
    "Label": "com.linkedin.daily-scanner.reply-check",
    "ProgramArguments": [
        "/usr/bin/caffeinate", "-i", python_bin, "-u", worker_file, "--schedule"
    ],
    "WorkingDirectory": project_dir,
    "RunAtLoad": True,
    "KeepAlive": True,
    "ProcessType": "Background",
    "EnvironmentVariables": {
        "HOME": home,
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
    },
    "StandardOutPath": f"{log_dir}/reply-check.out.log",
    "StandardErrorPath": f"{log_dir}/reply-check.err.log",
}
with open(plist_path, "wb") as output:
    plistlib.dump(payload, output)
PY

    /usr/bin/plutil -lint "$PLIST_PATH"
    launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
    launchctl bootstrap "$DOMAIN" "$PLIST_PATH"
    launchctl enable "$DOMAIN/$LABEL"
    echo "Reply-check schedule installed: 12:00 and 18:00 Asia/Ho_Chi_Minh"
    echo "Logs: $LOG_DIR/reply-check.out.log and reply-check.err.log"
    ;;
  status)
    launchctl print "$DOMAIN/$LABEL"
    ;;
  uninstall)
    launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
    if [[ -f "$PLIST_PATH" ]]; then
      mv "$PLIST_PATH" "$PLIST_PATH.disabled"
    fi
    echo "Reply-check schedule stopped. Plist kept at $PLIST_PATH.disabled"
    ;;
  *)
    echo "Usage: $0 [install|status|uninstall]" >&2
    exit 2
    ;;
esac
