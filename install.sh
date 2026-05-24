#!/usr/bin/env bash
set -euo pipefail

# Install script: creates virtualenv, installs requirements, and registers
# a systemd --user service to start the app at login/boot.

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$PROJECT_DIR/.venv"
PYTHON_CMD=python3

echo "Project directory: $PROJECT_DIR"

if ! command -v $PYTHON_CMD >/dev/null 2>&1; then
  echo "$PYTHON_CMD is not available. Install Python 3 and retry." >&2
  exit 1
fi

if [ ! -d "$VENV" ]; then
  echo "Creating virtualenv at $VENV"
  $PYTHON_CMD -m venv "$VENV"
fi

echo "Installing Python requirements into venv"
"$VENV/bin/python" -m pip install --upgrade pip setuptools >/dev/null
"$VENV/bin/python" -m pip install -r "$PROJECT_DIR/requirements.txt"

SERVICE_DIR="$HOME/.config/systemd/user"
mkdir -p "$SERVICE_DIR"
SERVICE_FILE="$SERVICE_DIR/pomodoro.service"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Pomodoro Timer (user)
After=graphical-session.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV/bin/python -m pomodoro
Restart=no
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
EOF

echo "Reloading systemd user daemon and enabling service"
systemctl --user daemon-reload
systemctl --user enable --now pomodoro.service

echo "Installation complete. Service enabled: pomodoro.service"
