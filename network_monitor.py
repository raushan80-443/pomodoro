#!/usr/bin/env python3
"""
Standalone 24/7 Network Latency & Slowdown Monitor for Linux.

Key Logic:
1. ONLY runs checks when connected to a local Wi-Fi / Hotspot network (has a default gateway).
   If Wi-Fi is turned off or disconnected, it stays completely silent (no false alarms).
2. When connected to Wi-Fi/Hotspot:
   Probes real internet latency to Google DNS (8.8.8.8) and Cloudflare (1.1.1.1).
3. If phone data is turned off, signal is lost, or latency exceeds 600ms continuously
   for 30 seconds:
   - Displays an unmissable on-screen floating toast alert.
   - Sends a desktop notification via notify-send.
   - Plays an audible alert chime.
4. When connection recovers, immediately shows a green '✓ Internet Restored' toast.
"""

import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

# Configurable defaults
SLOW_THRESHOLD_MS = int(os.environ.get("NETWORK_SLOW_THRESHOLD_MS", "600"))
SLOW_DURATION_SECONDS = int(os.environ.get("NETWORK_SLOW_DURATION_SECONDS", "30"))
CHECK_INTERVAL_SECONDS = int(os.environ.get("NETWORK_CHECK_INTERVAL", "4"))
ALERT_COOLDOWN_SECONDS = int(os.environ.get("NETWORK_ALERT_COOLDOWN", "120"))

PROBE_TARGETS = [
    ("8.8.8.8", 53),
    ("1.1.1.1", 53),
    ("google.com", 80),
]


def has_default_gateway():
    """
    Checks if a local network interface has an active default gateway via /proc/net/route.
    Returns (has_gateway: bool, interface_name: str or None)
    """
    try:
        with open("/proc/net/route", "r") as f:
            for line in f.readlines()[1:]:
                fields = line.strip().split()
                if len(fields) >= 4 and fields[1] == "00000000":
                    flags = int(fields[3], 16)
                    if flags & 0x2:  # RTF_GATEWAY
                        return True, fields[0]
    except Exception:
        pass

    # Fallback using ip route
    try:
        out = subprocess.check_output(["ip", "route"], timeout=1, stderr=subprocess.DEVNULL).decode()
        for line in out.splitlines():
            if line.startswith("default via"):
                parts = line.split()
                dev_idx = parts.index("dev") if "dev" in parts else -1
                dev_name = parts[dev_idx + 1] if dev_idx != -1 and dev_idx + 1 < len(parts) else "wifi"
                return True, dev_name
    except Exception:
        pass

    return False, None


def measure_internet_latency(timeout_sec=2.2):
    """
    Measures TCP connection latency to external servers in milliseconds.
    Returns (is_connected: bool, latency_ms: float or None, target_host: str)
    """
    for host, port in PROBE_TARGETS:
        t0 = time.time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout_sec)
            sock.connect((host, port))
            sock.close()
            latency = (time.time() - t0) * 1000.0
            return True, round(latency, 1), host
        except Exception:
            continue

    return False, None, "All targets unreachable"


def _ensure_display_env():
    """Ensures DISPLAY and XAUTHORITY are populated for GUI alerts."""
    if "DISPLAY" not in os.environ:
        os.environ["DISPLAY"] = ":0"
    if "XAUTHORITY" not in os.environ:
        xauth = Path.home() / ".Xauthority"
        if xauth.exists():
            os.environ["XAUTHORITY"] = str(xauth)


def play_alert_sound():
    """Plays audio chime alert."""
    sound_files = [
        "/usr/share/sounds/freedesktop/stereo/bell.oga",
        "/usr/share/sounds/freedesktop/stereo/message.oga",
        "/usr/share/sounds/oxygen/stereo/dialog-warning.ogg",
        "/usr/share/sounds/alsa/Front_Center.wav",
    ]
    for player in ["pw-play", "paplay", "aplay"]:
        for sf in sound_files:
            if Path(sf).exists():
                try:
                    subprocess.Popen([player, sf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
                except Exception:
                    pass
    try:
        subprocess.Popen(["spd-say", "-t", "female1", "network slow"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        pass
    print("\a", end="", flush=True)
    return True


def send_desktop_notification(title, message, urgency="normal"):
    """Sends native Linux desktop notification."""
    _ensure_display_env()
    try:
        subprocess.Popen(
            [
                "notify-send",
                "-u", urgency,
                "-t", "8000",
                "-a", "Network Monitor",
                title,
                message,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def show_floating_toast(title, message, bg_color="#7F1D1D", border_color="#EF4444", duration_ms=8000):
    """
    Displays a floating toast popup on the screen.
    Does not take away keyboard focus so typing is never interrupted.
    """
    def _worker():
        try:
            import tkinter as tk
            _ensure_display_env()

            root = tk.Tk()
            root.title("Network Status Alert")
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            root.configure(bg=bg_color)

            sw = root.winfo_screenwidth()
            w, h = 380, 96
            x = max(16, sw - w - 24)
            y = 42
            root.geometry(f"{w}x{h}+{x}+{y}")

            card = tk.Frame(root, bg=bg_color, highlightbackground=border_color, highlightthickness=2, padx=14, pady=10)
            card.pack(fill="both", expand=True)

            top_row = tk.Frame(card, bg=bg_color)
            top_row.pack(fill="x")

            title_lbl = tk.Label(
                top_row,
                text=title,
                font=("Helvetica", 11, "bold"),
                fg="#FEE2E2",
                bg=bg_color,
            )
            title_lbl.pack(side="left")

            close_lbl = tk.Label(
                top_row,
                text="✕",
                font=("Helvetica", 11, "bold"),
                fg="#9CA3AF",
                bg=bg_color,
                cursor="hand2",
            )
            close_lbl.pack(side="right")
            close_lbl.bind("<Button-1>", lambda e: root.destroy())

            msg_lbl = tk.Label(
                card,
                text=message,
                font=("Helvetica", 9),
                fg="#F9FAFB",
                bg=bg_color,
                justify="left",
                wraplength=348,
            )
            msg_lbl.pack(anchor="w", pady=(4, 0))

            card.bind("<Button-1>", lambda e: root.destroy())
            msg_lbl.bind("<Button-1>", lambda e: root.destroy())

            root.after(duration_ms, root.destroy)
            root.mainloop()
        except Exception as e:
            print(f"[NetworkMonitor] GUI Toast error: {e}", file=sys.stderr)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


class NetworkMonitor:
    def __init__(self, slow_threshold_ms=SLOW_THRESHOLD_MS, slow_duration=SLOW_DURATION_SECONDS):
        self.slow_threshold_ms = slow_threshold_ms
        self.slow_duration = slow_duration
        self.running = True
        self.slow_started_at = None
        self.alert_active = False
        self.last_alert_time = 0

    def check_once(self):
        has_net, iface = has_default_gateway()
        if not has_net:
            # User intentionally has Wi-Fi / Hotspot turned off.
            # Reset state and stay completely silent.
            self.slow_started_at = None
            self.alert_active = False
            return "NO_LOCAL_NETWORK"

        is_connected, latency, target = measure_internet_latency()
        is_slow = (not is_connected) or (latency is not None and latency >= self.slow_threshold_ms)

        now = time.time()
        if is_slow:
            if self.slow_started_at is None:
                self.slow_started_at = now

            duration = now - self.slow_started_at
            if duration >= self.slow_duration:
                if (not self.alert_active) or (now - self.last_alert_time >= ALERT_COOLDOWN_SECONDS):
                    self.alert_active = True
                    self.last_alert_time = now

                    if not is_connected:
                        title = "⚠️ No Internet Data (Phone Hotspot Down)"
                        msg = f"Connected to Wi-Fi ({iface}), but mobile data is OFF or unreachable for {int(duration)}s. Check phone!"
                    else:
                        title = "⚠️ Slow Network Detected"
                        msg = f"Connected to {iface}, but latency is very high ({latency}ms) for {int(duration)}s. Connections may lag."

                    print(f"\n[NetworkMonitor Alert] {title}\n  {msg}\n", flush=True)
                    play_alert_sound()
                    send_desktop_notification(title, msg, urgency="critical")
                    show_floating_toast(title, msg, bg_color="#450A0A", border_color="#EF4444")
                    return "ALERT_SLOW"
            return "DEGRADED_WAITING"
        else:
            # Network is healthy
            if self.alert_active:
                self.alert_active = False
                rec_title = "✓ Internet Restored"
                rec_msg = f"Latency normal ({latency}ms via {target}). Internet connection is healthy."
                print(f"\n[NetworkMonitor Recovery] {rec_title}: {rec_msg}\n", flush=True)
                send_desktop_notification(rec_title, rec_msg, urgency="low")
                show_floating_toast(rec_title, rec_msg, bg_color="#064E3B", border_color="#10B981", duration_ms=5000)

            self.slow_started_at = None
            return "HEALTHY"

    def run_forever(self):
        print(f"[NetworkMonitor] Monitoring internet health (Alerts when slow >{self.slow_threshold_ms}ms or down for >{self.slow_duration}s while connected to Wi-Fi).")
        while self.running:
            try:
                self.check_once()
            except Exception as e:
                print(f"[NetworkMonitor] Error in check loop: {e}", file=sys.stderr)
            time.sleep(CHECK_INTERVAL_SECONDS)


_daemon_thread = None

def start_network_monitor():
    """Starts monitor as a daemon thread in current process."""
    global _daemon_thread
    if _daemon_thread is None or not _daemon_thread.is_alive():
        mon = NetworkMonitor()
        _daemon_thread = threading.Thread(target=mon.run_forever, daemon=True, name="NetworkMonitorThread")
        _daemon_thread.start()
    return _daemon_thread


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("Testing single network check...")
        has_net, iface = has_default_gateway()
        print(f"1. Local Wi-Fi / Gateway present: {has_net} (Interface: {iface})")
        is_conn, lat, tgt = measure_internet_latency()
        print(f"2. Internet probe: connected={is_conn}, latency={lat}ms, target={tgt}")
        print("3. Spawning test toast alert & sound on display...")
        play_alert_sound()
        send_desktop_notification("⚠️ Test Alert: Slow Network", f"Connected to {iface}, latency test: {lat}ms")
        show_floating_toast("⚠️ Test Alert: Slow Network", f"Connected to {iface}, latency test: {lat}ms. Check phone hotspot.")
        time.sleep(2)
        print("Test complete!")
        sys.exit(0)

    # Run standalone daemon loop
    monitor = NetworkMonitor()
    try:
        monitor.run_forever()
    except KeyboardInterrupt:
        print("\nStopping network monitor.")
