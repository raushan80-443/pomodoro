# Pomodoro

Minimal Pomodoro timer application (work + break) with optional MongoDB sync.

**Prerequisites**
- Python 3.10+ installed.
- On Debian/Ubuntu install `python3-venv` to create virtual environments:

```bash
sudo apt update
sudo apt install -y python3-venv python3-tk
```

Note: `python3-tk` provides `tkinter` (GUI). Without it the app runs headless.

**Install (recommended: virtualenv)**

```bash
cd /path/to/pomodoro
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

**Optional: configure MongoDB sync**
Create `env/.env` (relative to project root) with values:

```
MONGODB_URI="mongodb+srv://user:password@cluster.example.com"
MONGODB_DB="myDatabase"
```

If `MONGODB_URI` is not set (or contains `<db_password>`), logs are kept locally in `pomodoro_log.json`.

**Run**

Start the app (from project root):

```bash
cd ..
python3 -m pomodoro
```

Quick tests (non-GUI):

```bash
python3 -c "from pomo import run_work_session; print(run_work_session(1))"
python3 -c "from pomo import run_break_session; print(run_break_session(1,2400,240))"
```

**Behavior notes**
- Work session: hidden/minimized so it does not cover other apps.
- Break session: fullscreen, always-on-top, attempts to grab input; shows an `Exit` button which saves and quits.
- Logs are written to `pomodoro_log.json` and synced to MongoDB when configured.
- Service mode waits 60 seconds after startup, then retries every 60 seconds until GUI display becomes available.

**Troubleshooting**
- If venv creation fails on Debian/Ubuntu: `sudo apt install python3-venv`.
- If GUI doesn't appear fullscreen, your desktop compositor may restrict fullscreen/override behaviors (Wayland vs X11). Run locally with a normal X session for best results.
- If logs show `GUI unavailable ... running headless`, the systemd user service likely does not have display variables. Re-run `./install.sh` and then restart with `systemctl --user restart pomodoro.service`.
- If logs show `No module named pomodoro.__main__` or package resolution errors, re-run `./install.sh`. The installer now sets a safe working directory for `python -m pomodoro`.
- Service retry timings are controlled by `POMODORO_DISPLAY_INITIAL_DELAY_SECONDS` and `POMODORO_DISPLAY_RETRY_SECONDS` in the generated user service.
