#!/bin/zsh
set -euo pipefail

LABEL="com.linkedin.daily-scanner.worker"
PROJECT_DIR="${1:-$HOME/Documents/linkedin-daily-scanner}"
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$PLIST_DIR/$LABEL.plist"
RUN_SCRIPT="$PROJECT_DIR/scripts/run_linkedin_worker.sh"
LOG_DIR="$PROJECT_DIR/logs"
UID_VALUE="$(id -u)"

if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "Project directory not found: $PROJECT_DIR" >&2
  exit 1
fi

if [[ ! -f "$PROJECT_DIR/linkedin_worker.py" ]]; then
  echo "linkedin_worker.py not found in: $PROJECT_DIR" >&2
  exit 1
fi

if [[ ! -f "$PROJECT_DIR/.env" ]]; then
  echo ".env not found in: $PROJECT_DIR" >&2
  exit 1
fi

if [[ ! -f "$RUN_SCRIPT" ]]; then
  echo "Runner script not found: $RUN_SCRIPT" >&2
  exit 1
fi

mkdir -p "$PLIST_DIR" "$LOG_DIR"
chmod +x "$RUN_SCRIPT"

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
    <string>$RUN_SCRIPT</string>
  </array>

  <key>WorkingDirectory</key>
  <string>$PROJECT_DIR</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>LINKEDIN_SCANNER_PROJECT_DIR</key>
    <string>$PROJECT_DIR</string>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>

  <key>RunAtLoad</key>
  <true/>

  <key>KeepAlive</key>
  <dict>
    <key>SuccessfulExit</key>
    <false/>
  </dict>

  <key>ThrottleInterval</key>
  <integer>10</integer>

  <key>ProcessType</key>
  <string>Background</string>

  <key>StandardOutPath</key>
  <string>$LOG_DIR/linkedin-worker.out.log</string>

  <key>StandardErrorPath</key>
  <string>$LOG_DIR/linkedin-worker.err.log</string>
</dict>
</plist>
PLIST

plutil -lint "$PLIST_PATH"

launchctl bootout "gui/$UID_VALUE/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$UID_VALUE" "$PLIST_PATH"
launchctl enable "gui/$UID_VALUE/$LABEL"
launchctl kickstart -k "gui/$UID_VALUE/$LABEL"

echo ""
echo "LinkedIn worker service installed."
echo "Label: $LABEL"
echo "Plist: $PLIST_PATH"
echo "Logs:"
echo "  $LOG_DIR/linkedin-worker.out.log"
echo "  $LOG_DIR/linkedin-worker.err.log"
echo ""
launchctl print "gui/$UID_VALUE/$LABEL" | head -n 35
