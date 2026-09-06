# ⚡ Pomodoro Analytics & Productivity Lock Timer (Tauri v2 + Rust)

A modern, ultra-lightweight Pomodoro timer and screen locker built for Linux using **Tauri v2 (Rust Core + Interactive Web UI)** with **embedded live graphical analytics**, hydration wellness cues, posture reminders, atomic local JSON persistence, and automated `systemd` user service integration.

---

## 📸 Analytics & Productivity Dashboard Preview

Every time you enter a break, the application dynamically computes your session history and renders a live, high-resolution dark-themed analytics dashboard directly inside the break lock screen:

![Pomodoro Graphical Analytics Dashboard](pomodoro_dashboard.png)

---

## 🌟 Key Features

* **⚡ Ultra-Lightweight Rust Engine (Tauri v2):**
  * Consumes ~25MB of RAM (vs 180MB+ in Python/Tkinter).
  * Native Linux input handling with **zero keyboard focus loss or text typing freezes under X11/Wayland**.
  * Instant startup (<100ms) with single native binary output.

* **💼 Distraction-Free Work Sessions (Default 40 mins):**
  * Sleek, compact dark window, dockable and unobtrusive.
  * Includes a **"Go On Break Now"** button to manually trigger a break when needed.
  * **✍️ Post-Session Note Prompt:** When work completes, an always-on-top modal prompts you to write a quick note, reflection, or next goal. Auto-dismisses in 10s if untouched, or **pauses the countdown as soon as you start typing** so you can take your time. Notes are saved to `pomodoro_log.json` (`sessionNote`).
  * Multi-stage sound alerts at 60s remaining and terminal/bell countdowns during the final 3s.
  * System sleep/suspend gap detection (>10s time drift) that automatically saves partial work and restarts a fresh cycle.

* **☕ Fullscreen Enforced Break Lock (Default 4 mins):**
  * Completely takes over the screen (fullscreen, borderless frame, topmost, input-grabbed, and auto-refocuses on focus loss).
  * **💧 Hydration Tracker ("Drink Water"):** Keep your focus sharp with a one-click water cup logger.
  * **🧘 Physical Reset Cues:** Rotating posture checks, 20-20-20 eye rest rule, and shoulder stretch prompts.
  * **💡 Long-Term Consistency Motivation:** Dynamic cues celebrating your active **39+ day focus streak**.
  * **⭐ Mandatory Rating Requirement:** You **cannot quit or resume work** until you click a 1–5 Star focus rating. Attempting to exit unrated flashes a warning and keeps the screen locked.
  * **📊 Live Responsive Canvas Charts:** Rendered on-the-fly from local JSON history:
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
  * **100% Backward-Compatible:** Preserves and visualizes your existing 556+ session history.

* **🛡️ Process Resilience & System Integration:**
  * Single instance process locking via Linux `fcntl.flock` on `pomodoro.lock`.
  * Audio engine supporting PipeWire (`pw-play`), PulseAudio (`paplay`), ALSA (`aplay`), and terminal bell.
  * `./install_tauri.sh` script for compiling and registering the `systemd --user` service.

---

## 🚀 Quick Start & Installation

### Option 1: Tauri v2 Native App (Recommended)
```bash
# 1. Build and install to ~/.local/bin/pomodoro and configure systemd
./install_tauri.sh

# 2. Start the service
systemctl --user enable --now pomodoro.service
```

### Option 2: Legacy Python/Tkinter Version
```bash
./install.sh
systemctl --user start pomodoro.service
```

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


