#!/usr/bin/env bash
set -euo pipefail

# Uninstall script: stops and disables the systemd --user service and removes
# the service file. Does not remove the virtualenv by default.

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_FILE="$HOME/.config/systemd/user/pomodoro.service"

echo "Stopping service (if running)"
systemctl --user stop pomodoro.service || true
echo "Disabling service"
systemctl --user disable pomodoro.service || true

if [ -f "$SERVICE_FILE" ]; then
  echo "Removing service file $SERVICE_FILE"
  rm -f "$SERVICE_FILE"
fi

echo "Reloading systemd user daemon"
systemctl --user daemon-reload

echo "Uninstall complete. Virtualenv and project files remain in $PROJECT_DIR"
