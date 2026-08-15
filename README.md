# ⚡ Pomodoro Analytics & Productivity Lock Timer

A minimal, distraction-free Pomodoro timer application (Work Session + Enforced Fullscreen Break) for Linux desktops, featuring **embedded live graphical analytics**, atomic local JSON logging, optional MongoDB cloud synchronization, audio chime notifications, and automated `systemd` user service integration.

---

## 📸 Analytics & Productivity Dashboard Preview

Every time you enter a break, the application dynamically computes your session history and renders a live, high-resolution dark-themed analytics dashboard directly inside the break lock screen:

![Pomodoro Graphical Analytics Dashboard](pomodoro_dashboard.png)

---

## 🌟 Key Features

* **💼 Distraction-Free Work Sessions (Default 40 mins):**
  * Runs in a small, sleek dark window (`720x420`), iconified/minimized by default so it stays out of your workspace.
  * Includes a **"Go On Break Now"** button to manually trigger a break when needed.
  * Multi-stage sound alerts at 60s remaining and terminal/Tkinter bell countdowns during the final 3s.
  * System sleep/suspend gap detection (>10s time drift) that automatically saves partial work and restarts a fresh cycle.

* **☕ Fullscreen Enforced Break Lock (Default 4 mins):**
  * Completely takes over the screen (fullscreen, borderless frame, topmost, input-grabbed, and auto-refocuses on focus loss).
  * **📊 Live Embedded Matplotlib Dashboard:** Rendered on-the-fly from local JSON history:
    * **Daily Focus Work Hours Over Time** (Line chart with gradient fill)
    * **Productivity Rating Distribution** (Bar chart across 1–5 stars)
    * **Work Session End Trigger Breakdown** (Donut chart for timer vs sleep vs manual break)
    * **Cumulative Focus Work Growth** (Area chart tracking overall focus hours)
  * **🎛️ Interactive Break Controls:**
    * Adjust current break duration (`-1 min` / `+1 min`).
    * Adjust next work session length (`Work -5 min` / `Work +5 min`).
    * **5-Star Productivity Rating Buttons:** Rate focus quality (`1: Low` to `5: Peak Focus`).
    * **Action Buttons:** **`⚡ RESUME WORK NOW`** and **`🔴 EXIT APP`**.

* **💾 Data Storage & Cloud Synchronization:**
  * **Atomic Local Storage:** All sessions are saved atomically to `pomodoro_log.json` (`syncStatus: "pending"`).
  * **Automatic MongoDB Sync:** When connected to the internet and `MONGODB_URI` is configured, pending sessions are automatically pushed to MongoDB (`pomodoro_sessions` collection) and marked `"synced"`. Works seamlessly offline.

* **🛡️ Process Resilience & System Integration:**
  * Single instance process locking via Linux `fcntl.flock` on `pomodoro.lock`.
  * Resolution-aware dynamic chart scaling fitting `1080p`, `4K`, and laptop screens automatically.
  * Audio engine supporting PipeWire (`pw-play`), PulseAudio (`paplay`), ALSA (`aplay`), Speech Synthesizer (`spd-say`), and Tkinter bells.
  * `./install.sh` and `./uninstall.sh` scripts for `systemd --user` service integration.

---

## 🛠️ Prerequisites

- **Python 3.10+**
- On Debian/Ubuntu systems, install `python3-venv` and `python3-tk`:

```bash
sudo apt update
sudo apt install -y python3-venv python3-tk
```

---

## 🚀 Installation & Running

### Option A: Automatic Linux Background Service (Recommended)
Run `./install.sh` to build the virtual environment, install requirements, and register a background `systemd --user` service that auto-starts on login:

```bash
./install.sh
```

To stop and remove the service:
```bash
./uninstall.sh
```

### Option B: Manual Setup & Execution

1. Create a virtual environment and install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

2. Run the Pomodoro app from the project root:
```bash
cd ..
python3 -m pomodoro
```

---

## 🧪 Sound Diagnostic Test

Verify system audio chime playback:
```bash
python3 -m pomodoro --test-sound
```

---

## ⚙️ Configuration & Environment Variables

Create `.env` (or `env/.env`) in the project root:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `MONGODB_URI` | *None* | Connection URI (e.g., `mongodb+srv://user:pass@cluster.mongodb.net`). If empty, logs stay local. |
| `MONGODB_DB` | `todoApp` | Target MongoDB database name. Collection used is `pomodoro_sessions`. |
| `POMODORO_SESSION_COUNT` | `1` | Total Pomodoro cycles to run before exiting. |
| `POMODORO_WAIT_FOR_DISPLAY` | `0` | Set to `1` to enable background waiting for X11/Wayland display readiness on boot. |
| `POMODORO_DISPLAY_INITIAL_DELAY_SECONDS` | `60` | Delay (seconds) before first display check in service mode. |
| `POMODORO_DISPLAY_RETRY_SECONDS` | `60` | Interval (seconds) between display availability retries. |

---

## 📁 File Structure

- `__init__.py`: Package entrypoint, MongoDB sync engine, session logger (atomic JSON writes), cycle runner.
- `pomo.py`: Tkinter work/break screens, graphical Matplotlib chart generator, audio chime engine, input lock.
- `pomodoro_log.json`: Local JSON database containing full session history and pending sync status.
- `pomodoro_dashboard.png`: High-resolution generated visual analytics dashboard image preview.
- `install.sh` / `uninstall.sh`: Installer and uninstaller for the Linux `systemd --user` background service.
- `requirements.txt`: Python package requirements (`pymongo`, `matplotlib`, `pandas`, `pillow`).


