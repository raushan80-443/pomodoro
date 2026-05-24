#!/usr/bin/env bash
set -euo pipefail

# Install script: creates virtualenv, installs requirements, and registers
# a systemd --user service to start the app at login/boot.

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$PROJECT_DIR/.venv"
PYTHON_CMD=python3
PIP_CMD=pip3

echo "Project directory: $PROJECT_DIR"

if ! command -v $PYTHON_CMD >/dev/null 2>&1; then
  echo "$PYTHON_CMD is not available. Install Python 3 and retry." >&2
  exit 1
fi

USE_VENV=0
if [ ! -d "$VENV" ]; then
  echo "Creating virtualenv at $VENV"
  $PYTHON_CMD -m venv "$VENV" || true
fi

# Check whether venv python has pip; if so use venv, otherwise fall back to
# installing requirements with system pip3 --user and run with system python3.
if [ -x "$VENV/bin/python" ]; then
  if "$VENV/bin/python" -m pip --version >/dev/null 2>&1; then
    USE_VENV=1
  else
    echo "venv Python has no pip; will fall back to using system pip3 and python3"
  fi
fi

SERVICE_DIR="$HOME/.config/systemd/user"
mkdir -p "$SERVICE_DIR"
SERVICE_FILE="$SERVICE_DIR/pomodoro.service"

if [ "$USE_VENV" -eq 1 ]; then
  echo "Installing Python requirements into venv"
  "$VENV/bin/python" -m pip install --upgrade pip setuptools
  "$VENV/bin/python" -m pip install -r "$PROJECT_DIR/requirements.txt"

[ -z "$SERVICE_FILE" ] || true
  cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Pomodoro Timer (user)
After=graphical-session.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV/bin/python -m pomodoro
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
EOF
else
  echo "Installing requirements with system pip3 --user"
  if ! command -v $PIP_CMD >/dev/null 2>&1; then
    echo "$PIP_CMD not found. Please install pip3 or enable venv ensurepip and retry." >&2
    exit 1
  fi
  $PIP_CMD install --user -r "$PROJECT_DIR/requirements.txt"

  # Use system python3 to run the app when venv isn't usable
[ -z "$SERVICE_FILE" ] || true
  cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Pomodoro Timer (user)
After=graphical-session.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=$(command -v $PYTHON_CMD) -m pomodoro
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
EOF
fi

echo "Reloading systemd user daemon and enabling service"
systemctl --user daemon-reload
systemctl --user enable --now pomodoro.service

echo "Installation complete. Service enabled: pomodoro.service"
