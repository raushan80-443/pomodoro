# ⚡ Pomodoro Focus System & System Resource Monitor (Linux & Windows)

A cross-platform Pomodoro productivity system, break locker, and real-time system performance monitor designed for **Linux** and **Windows**. Features include enforced daily skip limits, live CPU/RAM and network health monitoring, streamlined focus goal selections, graphical analytics dashboards, and automated boot/restart launchers.

---

## 🌟 Key Production Features

* **🔒 Strict Daily Skip Limit (Max 2 Early Continues / Skips per Day):**
  * Eliminates chronic break/work skipping to safeguard deep productivity.
  * You can early continue / skip work or break at most **2 times per calendar day**.
  * When 2 skips are exhausted, skip buttons are locked and display the explicit message:
    > **`"You have reached the limit and now nothing can be done after this. You have to wait."`**
  * Resuming when the break naturally completes (`00:00`) is unrestricted and does not consume skips.
  * Skips persist across reboots under `dailySkips[YYYY-MM-DD]` in `pomodoro_log.json` and browser `localStorage`.

* **💻 Live System Resource Performance Monitoring:**
  * Real-time metrics bar tracking:
    * **CPU Usage %**
    * **RAM Usage % and Memory Used / Total GB**
    * **Network Latency & Connectivity Status (ms)**
  * Displays continuously in the top navigation bar, work card, and break dashboard.
  * **High Resource Usage Alert**: When CPU or RAM hits $\ge 80\%$ for 15+ consecutive seconds, an unmistakable desktop notification and floating toast appear:
    > **`"High system resource usage: CPU is at X% and Memory is at Y%. Please cancel or close heavy applications."`**
  * Built-in 3-minute alert cooldown ensures zero notification spamming.

* **⏳ 2-Minute Pre-Break Heads-Up Warning:**
  * Upgraded from 1 minute to **2 minutes (120 seconds)**.
  * Spawns an executive 5-second floating toast allowing you ample time to wrap up thoughts, save open code/documents, and step away cleanly.

* **🎯 Streamlined Focus Goal & Fatigue-Free Launchpad:**
  * Replaced multi-part questionnaire barriers that led to mindless clicking with **one single intuitive focus question** (`💻 Deep Work / Code`, `📚 Study & Learn`, `🏋️ Exercise`, `🎯 Focus Target`) with default pre-selection.
  * Pre-selected 4★ focus rating with 1-click confirmation.
  * Daily routine checklist available as an optional wellness companion.

* **🌐 Network Health Monitoring (Jio Fiber / Portable):**
  * Continuously probes external TCP/DNS endpoints (`8.8.8.8`, `1.1.1.1`).
  * Distinguishes between intentional Wi-Fi disconnects and active connection stalls.
  * Plays audio chimes and shows instant recovery alert once latency normalizes.

* **🖥️ Native Cross-Platform Compatibility (Windows & Linux):**
  * **File Locking**: Automatic platform branching using `fcntl.flock` on Linux/macOS and `msvcrt.locking` on Windows.
  * **Notifications**: PowerShell Toast notifications on Windows, `notify-send` on Linux.
  * **Audio Alerts**: Native `winsound` chimes on Windows, PipeWire (`pw-play`), PulseAudio (`paplay`), ALSA (`aplay`), and `spd-say` on Linux.
  * **System Metrics**: `/proc/meminfo` and `psutil` on Linux; `psutil` and native Win32 memory status on Windows.

---

## 🚀 Windows Quick Start & Auto-Run

Windows batch scripts are provided in the repository root:

| Script | Purpose |
| :--- | :--- |
| **`run_pomodoro.bat`** | Auto-detects Python (`.venv`, `env`, or system Python), installs missing requirements, and launches Pomodoro. |
| **`run_pomodoro_silent.vbs`** | Launches Pomodoro in the background without leaving a black terminal window open on your screen. |
| **`install_autostart_windows.bat`** | **One-Click Auto-Run**: Configures Pomodoro to launch automatically on Windows restart/login via Startup folder and HKCU Run Registry key. |
| **`uninstall_autostart_windows.bat`** | Cleanly disables and removes all Windows auto-start entries. |

---

## 🐧 Linux Quick Start & Auto-Run

### Option 1: Automatic Systemd User Service (Auto-Start on Login)
```bash
./install.sh
```
To stop and disable:
```bash
./uninstall.sh
```

### Option 2: Run Directly via Python
```bash
# Activate virtual environment
source .venv/bin/activate

# Launch
python3 -m pomodoro
```

---

## 🧪 Automated Test Suite (33 Passing Test Cases)

The project includes an isolated, production-grade test suite covering skip limits, system monitoring, atomic storage, and cross-platform compatibility:

```bash
# Run the complete test suite
.venv/bin/pytest -v
```

### Test Coverage Breakdown:
* **`tests/test_skip_limit.py`**:
  * `test_initial_skips_remaining`
  * `test_record_single_skip`
  * `test_record_two_skips_exhausts_limit`
  * `test_record_beyond_limit_stays_at_zero_remaining`
  * `test_lock_message_string_exact_match`
  * `test_calendar_day_rollover`
  * `test_persistence_across_reloads`
  * `test_custom_max_skips_override`
  * `test_corrupt_log_recovery_during_skip_recording`
* **`tests/test_system_monitor.py`**:
  * `test_get_system_metrics_structure`
  * `test_high_resource_detection_cpu_trigger`
  * `test_high_resource_detection_ram_trigger`
  * `test_system_and_network_monitor_state_machine`
  * `test_has_default_gateway`
  * `test_resource_alert_cooldown_prevents_spam`
  * `test_network_monitor_recovery_detection`
* **`tests/test_pomodoro_core.py`**:
  * `test_warning_seconds_default_is_two_minutes`
  * `test_routine_completions_lifecycle`
  * `test_load_summary_stats_empty`
  * `test_time_slot_resolution`
  * `test_routine_schedule_structure`
  * `test_run_break_session_initialization`
* **`tests/test_storage_and_sync.py`**:
  * `test_load_json_log_missing_file`
  * `test_load_json_log_corrupt_file`
  * `test_write_and_load_json_log`
  * `test_get_pending_sessions`
  * `test_mark_sessions_synced`
  * `test_push_to_mongo_graceful_missing_uri`
* **`tests/test_cross_platform.py`**:
  * `test_lock_file_path_generation`
  * `test_single_instance_lock_acquisition_and_release`
  * `test_windows_batch_files_exist`
  * `test_linux_installer_scripts_exist`
  * `test_requirements_file_contains_core_dependencies`

---

## ⚙️ Environment Variables & Tuning

Create `.env` (or set system environment variables):

| Variable | Default | Description |
| :--- | :--- | :--- |
| `POMODORO_DAILY_MAX_SKIPS` | `2` | Max daily early continue / skip allowance. |
| `POMODORO_WARNING_SECONDS` | `120` | Pre-break warning trigger in seconds (default 2 mins). |
| `POMODORO_WORK_SECONDS` | `2400` | Work duration in seconds (default 40 mins). |
| `POMODORO_BREAK_SECONDS` | `240` | Break duration in seconds (default 4 mins). |
| `RESOURCE_CPU_THRESHOLD` | `80` | CPU % threshold for high resource warnings. |
| `RESOURCE_RAM_THRESHOLD` | `80` | RAM % threshold for high resource warnings. |
| `MONGODB_URI` | *None* | Optional remote MongoDB URI (e.g. `mongodb+srv://...`). If omitted, logs stay 100% local. |
| `MONGODB_DB` | `todoApp` | Target MongoDB database name. |
| `POMODORO_SESSION_COUNT` | `1` | Pomodoro cycles to run before exiting. |
| `POMODORO_LOG_PATH` | `./pomodoro_log.json` | Path to persistent JSON log file. |

---

## 📁 Repository Structure

```text
├── __init__.py                     # Package entry point, single-instance lock, sync engine
├── __main__.py                     # Executable module runner (`python -m pomodoro`)
├── pomo.py                         # Desktop GUI, skip gate logic, break screens, sound & warning toasts
├── network_monitor.py              # 24/7 cross-platform system resource & network health monitor
├── pomodoro_log.json               # Atomic local JSON database (sessions, routine completions, dailySkips)
├── requirements.txt                # Production dependencies (psutil, pymongo, matplotlib, pandas, pillow, pytest)
├── run_pomodoro.bat                # Windows interactive launcher
├── run_pomodoro_silent.vbs         # Windows background silent launcher
├── install_autostart_windows.bat   # Windows restart/boot auto-start installer
├── uninstall_autostart_windows.bat # Windows restart/boot auto-start uninstaller
├── install.sh                      # Linux systemd user service installer
├── uninstall.sh                    # Linux systemd user service uninstaller
├── tests/                          # 32-test automated unit and integration suite
│   ├── conftest.py
│   ├── test_skip_limit.py
│   ├── test_system_monitor.py
│   ├── test_pomodoro_core.py
│   ├── test_storage_and_sync.py
│   └── test_cross_platform.py
└── ui/                             # Web UI frontend assets (HTML, CSS, JS, Canvas Charts)
    ├── index.html
    ├── style.css
    ├── app.js
    └── charts.js
```
