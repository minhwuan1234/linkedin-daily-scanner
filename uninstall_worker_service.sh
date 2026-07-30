#!/bin/zsh
set -euo pipefail

LABEL="com.linkedin.daily-scanner.worker"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"
UID_VALUE="$(id -u)"

launchctl bootout "gui/$UID_VALUE/$LABEL" 2>/dev/null || true
rm -f "$PLIST_PATH"

echo "LinkedIn worker service removed."
