#!/bin/zsh

set -euo pipefail

SERVICE_LABEL="com.linkedin-daily-scanner.youtube-worker"
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
PLIST_PATH="$HOME/Library/LaunchAgents/${SERVICE_LABEL}.plist"
LOG_DIR="$PROJECT_ROOT/logs"
STDOUT_LOG="$LOG_DIR/youtube_worker.out.log"
STDERR_LOG="$LOG_DIR/youtube_worker.err.log"
USER_DOMAIN="gui/$(id -u)"

find_python() {
  if [[ -x "$PROJECT_ROOT/.venv/bin/python3" ]]; then
    printf '%s\n' "$PROJECT_ROOT/.venv/bin/python3"
    return
  fi

  command -v python3
}

write_plist() {
  local python_path
  python_path="$(find_python)"

  mkdir -p "$HOME/Library/LaunchAgents"
  mkdir -p "$LOG_DIR"

  cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC
  "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${SERVICE_LABEL}</string>

  <key>ProgramArguments</key>
  <array>
    <string>${python_path}</string>
    <string>-u</string>
    <string>${PROJECT_ROOT}/youtube_worker.py</string>
  </array>

  <key>WorkingDirectory</key>
  <string>${PROJECT_ROOT}</string>

  <key>RunAtLoad</key>
  <true/>

  <key>KeepAlive</key>
  <dict>
    <key>SuccessfulExit</key>
    <false/>
  </dict>

  <key>ProcessType</key>
  <string>Background</string>

  <key>StandardOutPath</key>
  <string>${STDOUT_LOG}</string>

  <key>StandardErrorPath</key>
  <string>${STDERR_LOG}</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PYTHONUNBUFFERED</key>
    <string>1</string>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
</dict>
</plist>
PLIST

  plutil -lint "$PLIST_PATH" >/dev/null
}

is_loaded() {
  launchctl print "${USER_DOMAIN}/${SERVICE_LABEL}" >/dev/null 2>&1
}

install_service() {
  write_plist

  if is_loaded; then
    launchctl bootout "${USER_DOMAIN}/${SERVICE_LABEL}" >/dev/null 2>&1 || true
  fi

  launchctl bootstrap "$USER_DOMAIN" "$PLIST_PATH"
  launchctl enable "${USER_DOMAIN}/${SERVICE_LABEL}"
  launchctl kickstart -k "${USER_DOMAIN}/${SERVICE_LABEL}"

  echo ""
  echo "YouTube worker service installed and started."
  show_status
}

start_service() {
  if [[ ! -f "$PLIST_PATH" ]]; then
    install_service
    return
  fi

  if ! is_loaded; then
    launchctl bootstrap "$USER_DOMAIN" "$PLIST_PATH"
  fi

  launchctl enable "${USER_DOMAIN}/${SERVICE_LABEL}"
  launchctl kickstart -k "${USER_DOMAIN}/${SERVICE_LABEL}"

  echo "YouTube worker started."
  show_status
}

stop_service() {
  if is_loaded; then
    launchctl bootout "${USER_DOMAIN}/${SERVICE_LABEL}"
    echo "YouTube worker stopped."
  else
    echo "YouTube worker is not loaded."
  fi
}

restart_service() {
  stop_service || true
  start_service
}

show_status() {
  echo ""
  echo "=============================="
  echo "YOUTUBE WORKER SERVICE"
  echo "=============================="
  echo "Label:   $SERVICE_LABEL"
  echo "Project: $PROJECT_ROOT"
  echo "Plist:   $PLIST_PATH"
  echo "Stdout:  $STDOUT_LOG"
  echo "Stderr:  $STDERR_LOG"

  if is_loaded; then
    echo "Status:  loaded"
    launchctl print "${USER_DOMAIN}/${SERVICE_LABEL}" \
      | grep -E 'state =|pid =|last exit code =' \
      | sed 's/^[[:space:]]*/  /' \
      || true
  else
    echo "Status:  stopped"
  fi
}

show_logs() {
  mkdir -p "$LOG_DIR"
  touch "$STDOUT_LOG" "$STDERR_LOG"

  echo "Following YouTube worker logs."
  echo "Press Ctrl+C to stop viewing logs."
  echo ""

  tail -n 80 -F "$STDOUT_LOG" "$STDERR_LOG"
}

uninstall_service() {
  if is_loaded; then
    launchctl bootout "${USER_DOMAIN}/${SERVICE_LABEL}" >/dev/null 2>&1 || true
  fi

  rm -f "$PLIST_PATH"

  echo "YouTube worker service uninstalled."
}

print_usage() {
  cat <<USAGE
Usage:
  ./youtube_worker_service.sh install
  ./youtube_worker_service.sh start
  ./youtube_worker_service.sh stop
  ./youtube_worker_service.sh restart
  ./youtube_worker_service.sh status
  ./youtube_worker_service.sh logs
  ./youtube_worker_service.sh uninstall
USAGE
}

command_name="${1:-}"

case "$command_name" in
  install)
    install_service
    ;;
  start)
    start_service
    ;;
  stop)
    stop_service
    ;;
  restart)
    restart_service
    ;;
  status)
    show_status
    ;;
  logs)
    show_logs
    ;;
  uninstall)
    uninstall_service
    ;;
  *)
    print_usage
    exit 1
    ;;
esac
