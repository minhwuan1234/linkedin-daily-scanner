#!/bin/zsh
set -euo pipefail

PROJECT_DIR="${LINKEDIN_SCANNER_PROJECT_DIR:-$HOME/Documents/linkedin-daily-scanner}"
ENV_FILE="$PROJECT_DIR/.env"
LOG_DIR="$PROJECT_DIR/logs"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python3"

mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "$(date -Iseconds) | Missing env file: $ENV_FILE" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

if [[ -x "$VENV_PYTHON" ]]; then
  PYTHON_BIN="$VENV_PYTHON"
else
  PYTHON_BIN="$(command -v python3)"
fi

echo "$(date -Iseconds) | Starting LinkedIn worker"
echo "$(date -Iseconds) | Project: $PROJECT_DIR"
echo "$(date -Iseconds) | Python: $PYTHON_BIN"

# Keep the Mac awake while the worker is active.
# The worker itself continuously polls Supabase for pending URLs.
exec /usr/bin/caffeinate -dimsu \
  "$PYTHON_BIN" \
  "$PROJECT_DIR/linkedin_worker.py"
