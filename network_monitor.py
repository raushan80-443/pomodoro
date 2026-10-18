#!/usr/bin/env python3
"""
Cross-Platform 24/7 System Resource & Network Health Monitor for Linux and Windows.

Key Capabilities:
1. Real-Time System Performance Monitoring:
   - Tracks CPU usage percentage and Memory (RAM) percentage & GB allocation.
   - Cross-platform support for both Linux and Windows.
   - Detects when system is under high resource stress (CPU >= 80% or RAM >= 80% for 15+ seconds).
   - Shows clear, non-confusing desktop notification and floating toast:
     "⚠️ High System Resource Usage: CPU at X%, Memory at Y%. Please cancel or close heavy applications."
2. Network Latency & Slowdown Monitoring:
   - Probes external latency to 8.8.8.8 and 1.1.1.1.
   - Detects when Wi-Fi / Hotspot or Jio Fiber network drops or experiences severe lag (>600ms).
   - Shows instant recovery toast when internet is restored.
3. Live Metric Extraction:
   - Provides get_system_metrics() for UI consumption across Pomodoro desktop & web dashboards.
"""

import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

# Optional psutil for high-accuracy cross-platform stats
try:
    import psutil
except ImportError:
    psutil = None

# Configurable defaults
SLOW_THRESHOLD_MS = int(os.environ.get("NETWORK_SLOW_THRESHOLD_MS", "600"))
SLOW_DURATION_SECONDS = int(os.environ.get("NETWORK_SLOW_DURATION_SECONDS", "30"))
CHECK_INTERVAL_SECONDS = int(os.environ.get("NETWORK_CHECK_INTERVAL", "4"))
ALERT_COOLDOWN_SECONDS = int(os.environ.get("NETWORK_ALERT_COOLDOWN", "120"))

# Resource thresholds
RESOURCE_CPU_THRESHOLD = int(os.environ.get("RESOURCE_CPU_THRESHOLD", "80"))
RESOURCE_RAM_THRESHOLD = int(os.environ.get("RESOURCE_RAM_THRESHOLD", "80"))
RESOURCE_ALERT_COOLDOWN = int(os.environ.get("RESOURCE_ALERT_COOLDOWN", "180"))  # 3 minutes

PROBE_TARGETS = [
    ("8.8.8.8", 53),
    ("1.1.1.1", 53),
    ("google.com", 80),
]


def has_default_gateway():
    """
    Checks if a local network interface has an active default gateway.
    Cross-platform: works on Linux (/proc/net/route, ip route) and Windows (socket connection).
    Returns (has_gateway: bool, interface_name: str or None)
    """
    if sys.platform == "win32":
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1.0)
            s.connect(("8.8.8.8", 80))
            s.close()
            return True, "Ethernet/Wi-Fi"
        except Exception:
            return False, None

    # Linux check via /proc/net/route
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

    # Linux fallback using ip route
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


def get_system_metrics():
    """
    Retrieves real-time system performance (CPU %, RAM %, RAM used/total GB, Network latency).
    Cross-platform for Linux and Windows with graceful native fallbacks.
    """
    cpu_pct = 0.0
    ram_pct = 0.0
    ram_used_gb = 0.0
    ram_total_gb = 0.0

    if psutil:
        try:
            cpu_pct = float(psutil.cpu_percent(interval=None))
            vm = psutil.virtual_memory()
            ram_pct = float(vm.percent)
            ram_used_gb = round(vm.used / (1024**3), 1)
            ram_total_gb = round(vm.total / (1024**3), 1)
        except Exception:
            pass
    elif sys.platform == "linux":
        try:
            # Read RAM from /proc/meminfo
            mem_info = {}
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip().split()[0]
                        mem_info[key] = int(val)
            total_kb = mem_info.get("MemTotal", 1)
            avail_kb = mem_info.get("MemAvailable", mem_info.get("MemFree", 0))
            used_kb = max(0, total_kb - avail_kb)
            ram_total_gb = round(total_kb / (1024**2), 1)
            ram_used_gb = round(used_kb / (1024**2), 1)
            ram_pct = round((used_kb / total_kb) * 100, 1)
        except Exception:
            pass

    # Fast probe for network latency
    is_conn, lat, target = measure_internet_latency(timeout_sec=0.8)
    if is_conn and lat is not None:
        net_status = f"Online ({int(lat)}ms)"
    elif is_conn:
        net_status = "Online"
    else:
        net_status = "Offline"

    is_high = bool(cpu_pct >= RESOURCE_CPU_THRESHOLD or ram_pct >= RESOURCE_RAM_THRESHOLD)
    reasons = []
    if cpu_pct >= RESOURCE_CPU_THRESHOLD:
        reasons.append(f"CPU at {cpu_pct:.0f}%")
    if ram_pct >= RESOURCE_RAM_THRESHOLD:
        reasons.append(f"Memory at {ram_pct:.0f}%")
    high_reason = " and ".join(reasons) if reasons else None

    return {
        "cpu_percent": cpu_pct,
        "memory_percent": ram_pct,
        "memory_used_gb": ram_used_gb,
        "memory_total_gb": ram_total_gb,
        "network_connected": is_conn,
        "network_latency": lat,
        "network_target": target,
        "network_status": net_status,
        "is_high_usage": is_high,
        "high_usage_reason": high_reason,
    }


def find_active_xauthority():
    """Finds valid Xauthority file on modern Linux desktop systems."""
    if sys.platform != "linux":
        return None
    curr = os.environ.get("XAUTHORITY")
    if curr and Path(curr).exists():
        return curr
    runtime_dir = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    if runtime_dir.exists():
        candidates = sorted(runtime_dir.glob("xauth_*"))
        if candidates:
            return str(candidates[-1])
    home_auth = Path.home() / ".Xauthority"
    if home_auth.exists():
        return str(home_auth)
    return None


def _ensure_display_env():
    """Ensures DISPLAY and XAUTHORITY are populated on Linux GUI environments."""
    if sys.platform != "linux":
        return
    if "DISPLAY" not in os.environ or not os.environ["DISPLAY"]:
        os.environ["DISPLAY"] = ":0"
    xauth = find_active_xauthority()
    if xauth:
        os.environ["XAUTHORITY"] = xauth


def play_alert_sound(mode="warning"):
    """Plays audio chime alert for warning or positive recovery across Windows and Linux."""
    if sys.platform == "win32":
        try:
            import winsound
            if mode == "recovery":
                winsound.MessageBeep(winsound.MB_OK)
            else:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            return True
        except Exception:
            pass

    # Linux sound players
    if mode == "recovery":
        sound_files = [
            "/usr/share/sounds/freedesktop/stereo/network-connectivity-established.oga",
            "/usr/share/sounds/freedesktop/stereo/complete.oga",
            "/usr/share/sounds/freedesktop/stereo/message.oga",
            "/usr/share/sounds/oxygen/stereo/dialog-information.ogg",
        ]
    else:
        sound_files = [
            "/usr/share/sounds/freedesktop/stereo/network-connectivity-lost.oga",
            "/usr/share/sounds/freedesktop/stereo/dialog-warning.oga",
            "/usr/share/sounds/freedesktop/stereo/bell.oga",
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
        phrase = "internet restored" if mode == "recovery" else "alert"
        subprocess.Popen(["spd-say", "-t", "female1", phrase], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        pass

    print("\a", end="", flush=True)
    return True


def send_desktop_notification(title, message, urgency="normal"):
    """Sends native desktop notification on both Linux and Windows."""
    if sys.platform == "win32":
        # Windows PowerShell Toast Notification
        ps_script = (
            "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null; "
            "$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
            "$t = $template.GetElementsByTagName('text'); "
            f"$t.Item(0).AppendChild($template.CreateTextNode('{title}')) | Out-Null; "
            f"$t.Item(1).AppendChild($template.CreateTextNode('{message}')) | Out-Null; "
            "$toast = [Windows.UI.Notifications.ToastNotification]::new($template); "
            "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Pomodoro').Show($toast);"
        )
        try:
            subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            pass

    _ensure_display_env()
    try:
        subprocess.Popen(
            [
                "notify-send",
                "-u", urgency,
                "-t", "6000",
                "-a", "Pomodoro System Monitor",
                title,
                message,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        pass
    return False


_toast_subprocess = None
_toast_lock = threading.Lock()


def dismiss_floating_toast():
    """Immediately terminates any active on-screen toast window."""
    global _toast_subprocess
    with _toast_lock:
        if _toast_subprocess and _toast_subprocess.poll() is None:
            try:
                _toast_subprocess.terminate()
                _toast_subprocess.kill()
            except Exception:
                pass
            _toast_subprocess = None


def show_floating_toast(title, message, bg_color="#450A0A", border_color="#EF4444", duration_ms=8000):
    """
    Spawns an isolated, self-terminating subprocess toast window across Windows and Linux.
    Guaranteed to auto-exit after duration_ms or on click.
    """
    global _toast_subprocess
    _ensure_display_env()
    dismiss_floating_toast()

    display = os.environ.get("DISPLAY", ":0") if sys.platform == "linux" else ""
    xauth = os.environ.get("XAUTHORITY", "") if sys.platform == "linux" else ""

    toast_code = f"""
import os, sys, tkinter as tk
if sys.platform == "linux":
    os.environ['DISPLAY'] = {display!r}
    if {xauth!r}:
        os.environ['XAUTHORITY'] = {xauth!r}

try:
    root = tk.Tk()
    root.title('System Alert')
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    root.configure(bg={bg_color!r})

    sw = root.winfo_screenwidth()
    w, h = 420, 105
    x = max(16, sw - w - 24)
    y = 42
    root.geometry(f'{{w}}x{{h}}+{{x}}+{{y}}')

    card = tk.Frame(root, bg={bg_color!r}, highlightbackground={border_color!r}, highlightthickness=2, padx=16, pady=10)
    card.pack(fill='both', expand=True)

    top_row = tk.Frame(card, bg={bg_color!r})
    top_row.pack(fill='x')

    fg_title = '#FEE2E2' if {bg_color!r} != '#064E3B' else '#D1FAE5'
    title_lbl = tk.Label(top_row, text={title!r}, font=('Helvetica', 11, 'bold'), fg=fg_title, bg={bg_color!r})
    title_lbl.pack(side='left')

    close_lbl = tk.Label(top_row, text='✕', font=('Helvetica', 11, 'bold'), fg='#9CA3AF', bg={bg_color!r}, cursor='hand2')
    close_lbl.pack(side='right')
    close_lbl.bind('<Button-1>', lambda e: sys.exit(0))

    msg_lbl = tk.Label(card, text={message!r}, font=('Helvetica', 9), fg='#F9FAFB', bg={bg_color!r}, justify='left', wraplength=384)
    msg_lbl.pack(anchor='w', pady=(4, 0))

    card.bind('<Button-1>', lambda e: sys.exit(0))
    msg_lbl.bind('<Button-1>', lambda e: sys.exit(0))
    title_lbl.bind('<Button-1>', lambda e: sys.exit(0))

    root.after({duration_ms}, lambda: sys.exit(0))
    root.mainloop()
except Exception:
    sys.exit(0)
"""

    with _toast_lock:
        try:
            _toast_subprocess = subprocess.Popen(
                [sys.executable, "-c", toast_code],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            print(f"[SystemMonitor] Subprocess toast spawn error: {e}", file=sys.stderr)


class SystemAndNetworkMonitor:
    """
    Unified 24/7 Monitor for both System Performance (CPU/RAM) and Network Health (Jio Fiber/Hotspot).
    """
    def __init__(
        self,
        slow_threshold_ms=SLOW_THRESHOLD_MS,
        slow_duration=SLOW_DURATION_SECONDS,
        cpu_threshold=RESOURCE_CPU_THRESHOLD,
        ram_threshold=RESOURCE_RAM_THRESHOLD,
    ):
        self.slow_threshold_ms = slow_threshold_ms
        self.slow_duration = slow_duration
        self.cpu_threshold = cpu_threshold
        self.ram_threshold = ram_threshold
        self.running = True

        # Network alert tracking
        self.slow_started_at = None
        self.alert_active = False
        self.last_net_alert_time = 0

        # System resource alert tracking
        self.resource_stressed_started_at = None
        self.last_resource_alert_time = 0

    def check_system_resources_once(self):
        """Monitors CPU and RAM; alerts if system is running heavy under sustained load."""
        metrics = get_system_metrics()
        now = time.time()

        if metrics["is_high_usage"]:
            if self.resource_stressed_started_at is None:
                self.resource_stressed_started_at = now

            duration = now - self.resource_stressed_started_at
            # Sustained high usage for at least 15 seconds
            if duration >= 15:
                if (now - self.last_resource_alert_time) >= RESOURCE_ALERT_COOLDOWN:
                    self.last_resource_alert_time = now
                    title = "⚠️ High System Resource Usage"
                    msg = (
                        f"System resources are high: CPU is at {metrics['cpu_percent']:.0f}% and "
                        f"Memory is at {metrics['memory_percent']:.0f}% "
                        f"({metrics['memory_used_gb']:.1f} GB / {metrics['memory_total_gb']:.1f} GB used). "
                        f"Please cancel or close heavy applications to keep your computer running smoothly."
                    )
                    toast_msg = (
                        f"CPU: {metrics['cpu_percent']:.0f}%  •  RAM: {metrics['memory_percent']:.0f}% "
                        f"({metrics['memory_used_gb']:.1f}/{metrics['memory_total_gb']:.1f} GB)\n"
                        f"High resource usage detected. Please cancel or close some applications."
                    )
                    print(f"\n[SystemMonitor Alert] {title}\n  {msg}\n", flush=True)
                    play_alert_sound("warning")
                    send_desktop_notification(title, msg, urgency="critical")
                    show_floating_toast(title, toast_msg, bg_color="#450A0A", border_color="#EF4444", duration_ms=9000)
                    return "ALERT_HIGH_RESOURCES"
            return "STRESSED_WAITING"
        else:
            self.resource_stressed_started_at = None
            return "RESOURCES_HEALTHY"

    def check_network_once(self):
        """Monitors network latency and connection status."""
        has_net, iface = has_default_gateway()
        if not has_net:
            # Wi-Fi turned off intentionally or no local gateway. Stay silent.
            self.slow_started_at = None
            self.alert_active = False
            return "NO_LOCAL_NETWORK"

        probe_timeout = 1.0 if self.alert_active else 2.2
        is_connected, latency, target = measure_internet_latency(timeout_sec=probe_timeout)
        is_slow = (not is_connected) or (latency is not None and latency >= self.slow_threshold_ms)

        now = time.time()
        if is_slow:
            if self.slow_started_at is None:
                self.slow_started_at = now

            duration = now - self.slow_started_at
            if duration >= self.slow_duration:
                if (not self.alert_active) or (now - self.last_net_alert_time >= ALERT_COOLDOWN_SECONDS):
                    self.alert_active = True
                    self.last_net_alert_time = now

                    if not is_connected:
                        title = "⚠️ Internet Connection Down"
                        msg = f"Network interface ({iface}) connected, but internet is unreachable for {int(duration)}s. Check network / fiber connection."
                    else:
                        title = "⚠️ Slow Network Detected"
                        msg = f"Connected to {iface}, but latency is very high ({latency}ms) for {int(duration)}s. Connections may lag."

                    print(f"\n[NetworkMonitor Alert] {title}\n  {msg}\n", flush=True)
                    play_alert_sound("warning")
                    send_desktop_notification(title, msg, urgency="critical")
                    show_floating_toast(title, msg, bg_color="#450A0A", border_color="#EF4444", duration_ms=10000)
                    return "ALERT_SLOW"
            return "DEGRADED_WAITING"
        else:
            if self.alert_active:
                self.alert_active = False
                rec_title = "✓ Internet Restored"
                rec_msg = f"Latency normal ({latency}ms via {target}). Internet connection is healthy!"
                print(f"\n[NetworkMonitor Recovery] {rec_title}: {rec_msg}\n", flush=True)
                play_alert_sound("recovery")
                send_desktop_notification(rec_title, rec_msg, urgency="low")
                show_floating_toast(rec_title, rec_msg, bg_color="#064E3B", border_color="#10B981", duration_ms=4000)

            self.slow_started_at = None
            return "HEALTHY"

    def run_forever(self):
        print(f"[System & Network Monitor] Running. Monitoring CPU/RAM (alert on >{self.cpu_threshold}% CPU or >{self.ram_threshold}% RAM) and network latency.")
        while self.running:
            try:
                self.check_system_resources_once()
            except Exception as e:
                print(f"[SystemMonitor] Error in resource check: {e}", file=sys.stderr)

            try:
                self.check_network_once()
            except Exception as e:
                print(f"[NetworkMonitor] Error in network check: {e}", file=sys.stderr)

            poll_interval = 1.0 if self.alert_active else CHECK_INTERVAL_SECONDS
            time.sleep(poll_interval)


_daemon_thread = None


def start_system_and_network_monitor():
    """Starts unified system and network monitor in a background daemon thread."""
    global _daemon_thread
    if _daemon_thread is None or not _daemon_thread.is_alive():
        mon = SystemAndNetworkMonitor()
        _daemon_thread = threading.Thread(target=mon.run_forever, daemon=True, name="SystemNetworkMonitorThread")
        _daemon_thread.start()
    return _daemon_thread


# Alias for backward compatibility
start_network_monitor = start_system_and_network_monitor


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("Testing System & Network Monitor...")
        metrics = get_system_metrics()
        print(f"1. CPU Usage: {metrics['cpu_percent']}%")
        print(f"2. RAM Usage: {metrics['memory_percent']}% ({metrics['memory_used_gb']} GB / {metrics['memory_total_gb']} GB)")
        print(f"3. Network: {metrics['network_status']} (Target: {metrics['network_target']})")
        print("4. Testing alert toast & sound...")
        play_alert_sound()
        send_desktop_notification("⚠️ Test Alert", f"System: CPU {metrics['cpu_percent']}%, RAM {metrics['memory_percent']}%")
        show_floating_toast("⚠️ Test Alert", f"CPU: {metrics['cpu_percent']}%, RAM: {metrics['memory_percent']}%. System monitor working properly.")
        time.sleep(2)
        print("Test complete!")
        sys.exit(0)

    monitor = SystemAndNetworkMonitor()
    try:
        monitor.run_forever()
    except KeyboardInterrupt:
        print("\nStopping monitor.")
