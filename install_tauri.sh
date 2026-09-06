#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_SRC="$PROJECT_DIR/src-tauri/target/release/pomodoro"
TARGET_BIN="$HOME/.local/bin/pomodoro"
SERVICE_NAME="pomodoro.service"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_PATH="$SERVICE_DIR/$SERVICE_NAME"

echo "=== Installing Tauri v2 Pomodoro Linux Application ==="

# 1. Build if release binary does not exist
if [ ! -f "$BIN_SRC" ]; then
    echo "Building release binary..."
    cd "$PROJECT_DIR"
    cargo build --release --manifest-path src-tauri/Cargo.toml
fi

# 2. Copy binary to ~/.local/bin
mkdir -p "$HOME/.local/bin"
cp "$BIN_SRC" "$TARGET_BIN"
chmod +x "$TARGET_BIN"
echo "✓ Installed binary to $TARGET_BIN"

# 3. Create systemd user service
mkdir -p "$SERVICE_DIR"
cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=Pomodoro Desktop Service (Tauri v2)
After=graphical-session.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=$TARGET_BIN
Restart=on-failure
RestartSec=3
Environment=DISPLAY=:0
Environment=XAUTHORITY=%h/.Xauthority

[Install]
WantedBy=default.target
EOF

echo "✓ Created systemd unit: $SERVICE_PATH"

# 4. Reload and enable systemd user daemon
systemctl --user daemon-reload
echo ""
echo "To start the background Pomodoro service now, run:"
echo "  systemctl --user enable --now $SERVICE_NAME"
echo ""
echo "To run interactively from terminal:"
echo "  $TARGET_BIN"
echo ""
echo "=== Installation Ready! ==="
