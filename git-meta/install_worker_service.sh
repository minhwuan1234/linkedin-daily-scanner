#!/bin/zsh
set -euo pipefail

LABEL="com.linkedin.daily-scanner.worker"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$PLIST_DIR/$LABEL.plist"

LOG_DIR="$PROJECT_DIR/logs"
OUT_LOG="$LOG_DIR/linkedin-worker.out.log"
ERR_LOG="$LOG_DIR/linkedin-worker.err.log"

PYTHON_BIN="$PROJECT_DIR/.venv/bin/python3"
WORKER_FILE="$PROJECT_DIR/linkedin_worker.py"
ENV_FILE="$PROJECT_DIR/.env"

DOMAIN="gui/$(id -u)"

if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "Project directory not found: $PROJECT_DIR" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo ".env not found: $ENV_FILE" >&2
  exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Virtualenv Python not found: $PYTHON_BIN" >&2
  exit 1
fi

if [[ ! -f "$WORKER_FILE" ]]; then
  echo "Worker file not found: $WORKER_FILE" >&2
  exit 1
fi

mkdir -p "$PLIST_DIR"
mkdir -p "$LOG_DIR"

launchctl bootout \
  "$DOMAIN/$LABEL" \
  2>/dev/null || true

rm -f "$PLIST_PATH"

COMMAND="cd '$PROJECT_DIR' && set -a && source '$ENV_FILE' && set +a && exec /usr/bin/caffeinate -dimsu '$PYTHON_BIN' -u '$WORKER_FILE'"

ESCAPED_COMMAND="$(
  printf '%s' "$COMMAND" \
    | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g'
)"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">

<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-lc</string>
    <string>$ESCAPED_COMMAND</string>
  </array>

  <key>WorkingDirectory</key>
  <string>$PROJECT_DIR</string>

  <key>RunAtLoad</key>
  <true/>

  <key>KeepAlive</key>
  <true/>

  <key>ThrottleInterval</key>
  <integer>10</integer>

  <key>ProcessType</key>
  <string>Interactive</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>HOME</key>
    <string>$HOME</string>

    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>

  <key>StandardOutPath</key>
  <string>$OUT_LOG</string>

  <key>StandardErrorPath</key>
  <string>$ERR_LOG</string>
</dict>
</plist>
PLIST

/usr/bin/plutil -lint "$PLIST_PATH"

: > "$OUT_LOG"
: > "$ERR_LOG"

launchctl bootstrap \
  "$DOMAIN" \
  "$PLIST_PATH"

launchctl enable \
  "$DOMAIN/$LABEL"

launchctl kickstart -k \
  "$DOMAIN/$LABEL"

sleep 4

echo ""
echo "LinkedIn worker service installed."
echo "Label: $LABEL"
echo "Project: $PROJECT_DIR"
echo "Plist: $PLIST_PATH"
echo ""

launchctl print \
  "$DOMAIN/$LABEL" \
  | grep -E "state =|pid =|last exit code" \
  || true

echo ""
echo "Output log:"
echo "$OUT_LOG"
echo ""
echo "Error log:"
echo "$ERR_LOG"
