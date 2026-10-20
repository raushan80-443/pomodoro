import io
import json
import os
import random
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

try:
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import pandas as pd
    from PIL import Image, ImageTk
except ImportError:
    mdates = None
    plt = None
    pd = None
    Image = None
    ImageTk = None

os.environ["MPLCONFIGDIR"] = tempfile.gettempdir()

try:
    from .network_monitor import get_system_metrics, send_desktop_notification
except Exception:
    try:
        from network_monitor import get_system_metrics, send_desktop_notification
    except Exception:
        get_system_metrics = None
        send_desktop_notification = None

MIN_DURATION_SECONDS = 60
SUSPEND_GAP_SECONDS = 10
_HEADLESS_WARNING_EMITTED = False

MOTIVATIONAL_QUOTES = [
    "Focus is a muscle: every deep work session strengthens your discipline.",
    "Small daily disciplines compounding over time produce extraordinary results.",
    "Deep work is the superpower of the 21st century. Protect your attention.",
    "Discipline is choosing between what you want now and what you want most.",
    "Rest is not idleness; it is the vital recharge that fuels breakthrough thinking.",
    "Energy flows where attention goes. Consistency creates momentum.",
    "You don't need more time, you need more focused, undistracted presence.",
    "One session at a time. Show up, lock in, execute, recharge.",
]

DEFAULT_ROUTINE_SCHEDULE = {
    "morning": {
        "name": "🌅 MORNING ROUTINE (7:00 - 11:00 AM)",
        "tasks": [
            {
                "id": "brush",
                "title": "🪥 Go and do brush / Wash face",
                "desc": "Freshen up, clean teeth, and splash cold water to wake up.",
            },
            {
                "id": "exercise",
                "title": "🏋️ Exercise time / Workout & physical training",
                "desc": "Exercise time! Pushups, stretching, cardio, or morning workout.",
            },
            {
                "id": "bath",
                "title": "🚿 Take a bath and freshen up",
                "desc": "Take a refreshing bath to reset body temperature & elevate alertness.",
            },
            {
                "id": "breakfast",
                "title": "🍳 Eat some food / Have breakfast",
                "desc": "Fuel your brain & body with a nourishing, healthy breakfast.",
            },
            {
                "id": "water_am",
                "title": "💧 Drink a tall glass of water",
                "desc": "Rehydrate after sleep to kickstart cognitive energy.",
            },
            {
                "id": "stretch_am",
                "title": "🧘 5-minute stretch & sunlight",
                "desc": "Loosen up spine and get natural light exposure.",
            },
        ],
    },
    "afternoon": {
        "name": "☀️ AFTERNOON RECHARGE & HYDRATION",
        "tasks": [
            {
                "id": "water_pm",
                "title": "💧 Drink a full glass of water",
                "desc": "Brain speed and stamina drop with even 1% dehydration. Rehydrate now!",
            },
            {
                "id": "exercise_pm",
                "title": "🏋️ Quick exercise / Mobility & body movement",
                "desc": "10 squats, pushups, jumping jacks, or brisk walk to recharge energy.",
            },
            {
                "id": "eyes_pm",
                "title": "👀 20-20-20 Eye relaxation",
                "desc": "Focus on an object 20 feet away for 20 seconds to reset eye muscles.",
            },
            {
                "id": "posture_pm",
                "title": "🧘 Posture reset & shoulder roll",
                "desc": "Roll shoulders back, unlock jaw, and straighten spinal alignment.",
            },
            {
                "id": "walk_pm",
                "title": "🚶 Quick 2-min walk & stretch",
                "desc": "Step away from desk to restore active blood circulation.",
            },
        ],
    },
    "evening": {
        "name": "🌆 EVENING RESET & WIND-DOWN",
        "tasks": [
            {
                "id": "water_eve",
                "title": "💧 Hydration check: Drink fresh water",
                "desc": "Keep hydration steady through the evening.",
            },
            {
                "id": "exercise_eve",
                "title": "🏋️ Evening walk & light workout",
                "desc": "Brisk walking or evening core & mobility exercise.",
            },
            {
                "id": "walk_eve",
                "title": "🚶 Evening stroll & fresh air",
                "desc": "Step outside for 10 minutes to decompress cognitive load.",
            },
            {
                "id": "plan_eve",
                "title": "📋 Review accomplishments & plan next day",
                "desc": "List your top 3 priority tasks for tomorrow morning.",
            },
            {
                "id": "relax_eve",
                "title": "🌙 Dim ambient light & eye reset",
                "desc": "Transition nervous system toward restorative rest.",
            },
        ],
    },
}


def _get_log_path():
    """Returns path to pomodoro_log.json, respecting POMODORO_LOG_PATH if set."""
    custom = os.environ.get("POMODORO_LOG_PATH")
    if custom:
        return Path(custom)
    return Path(__file__).resolve().parent / "pomodoro_log.json"


def _get_time_slot():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    else:
        return "evening"


def _load_routine_completions():
    log_path = _get_log_path()
    if not log_path.exists():
        return []
    try:
        data = json.loads(log_path.read_text())
        completions = data.get("routineCompletions", [])
        today_str = datetime.now().strftime("%Y-%m-%d")
        return [c for c in completions if c.get("date") == today_str]
    except Exception:
        return []


def _save_routine_completion(task_id, task_title=""):
    log_path = _get_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    now_iso = datetime.now().isoformat() + "Z"

    data = {"appName": "pomodoro", "createdAt": now_iso, "events": []}
    if log_path.exists():
        try:
            data = json.loads(log_path.read_text())
        except Exception:
            data = {"appName": "pomodoro", "createdAt": now_iso, "events": []}

    completions = data.get("routineCompletions", [])
    already_done = any(c.get("taskId") == task_id and c.get("date") == today_str for c in completions)
    if not already_done:
        completions.append({
            "taskId": task_id,
            "taskTitle": task_title,
            "date": today_str,
            "completedAt": now_iso,
        })
        data["routineCompletions"] = completions
        temp_path = log_path.with_suffix(".json.tmp")
        try:
            temp_path.write_text(json.dumps(data, indent=2))
            os.replace(temp_path, log_path)
        except Exception:
            log_path.write_text(json.dumps(data, indent=2))


MAX_DAILY_SKIPS = int(os.environ.get("POMODORO_DAILY_MAX_SKIPS", "2"))
WARNING_SECONDS = int(os.environ.get("POMODORO_WARNING_SECONDS", "120"))


def _load_daily_skips(date_str=None):
    """Loads recorded skips/early continues for the given day (default: today)."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    log_path = _get_log_path()
    if not log_path.exists():
        return []
    try:
        data = json.loads(log_path.read_text())
        daily_skips = data.get("dailySkips", {})
        return daily_skips.get(date_str, [])
    except Exception:
        return []


def _record_daily_skip(skip_type="break_early_continue"):
    """Records an early skip / continue event for today."""
    log_path = _get_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    now_iso = datetime.now().isoformat() + "Z"

    data = {"appName": "pomodoro", "createdAt": now_iso, "events": []}
    if log_path.exists():
        try:
            data = json.loads(log_path.read_text())
        except Exception:
            data = {"appName": "pomodoro", "createdAt": now_iso, "events": []}

    daily_skips = data.get("dailySkips", {})
    day_list = daily_skips.get(date_str, [])
    day_list.append({
        "timestamp": now_iso,
        "type": skip_type,
    })
    daily_skips[date_str] = day_list
    data["dailySkips"] = daily_skips

    temp_path = log_path.with_suffix(".json.tmp")
    try:
        temp_path.write_text(json.dumps(data, indent=2))
        os.replace(temp_path, log_path)
    except Exception:
        log_path.write_text(json.dumps(data, indent=2))
    return len(day_list)


def _get_skips_remaining(max_skips=None):
    """Returns (skips_remaining, skips_used) for today."""
    if max_skips is None:
        max_skips = MAX_DAILY_SKIPS
    skips_used = len(_load_daily_skips())
    return max(0, max_skips - skips_used), skips_used



def _show_locked_warning_toast(root, message="You have reached the limit and now nothing can be done after this. You have to wait."):
    """Shows an unmistakable modal alert when user attempts to skip beyond the 2-skips/day limit."""
    import tkinter as tk
    try:
        toast = tk.Toplevel(root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg="#DC2626")

        card = tk.Frame(toast, bg="#450A0A", padx=26, pady=16, highlightbackground="#EF4444", highlightthickness=2)
        card.pack(padx=2, pady=2, fill="both", expand=True)

        tk.Label(
            card,
            text="🔒 DAILY SKIP LIMIT REACHED (2/2 USED)",
            font=("Helvetica", 14, "bold"),
            fg="#FEE2E2",
            bg="#450A0A",
        ).pack()

        tk.Label(
            card,
            text=message,
            font=("Helvetica", 11, "bold"),
            fg="#FCA5A5",
            bg="#450A0A",
            wraplength=480,
            justify="center",
        ).pack(pady=(8, 12))

        close_btn = tk.Button(
            card,
            text="I Understand — Waiting For Timer ⌛",
            font=("Helvetica", 11, "bold"),
            bg="#7F1D1D",
            fg="#FFFFFF",
            activebackground="#991B1B",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=18,
            pady=6,
            command=toast.destroy,
        )
        close_btn.pack()

        toast.update_idletasks()
        w = max(500, toast.winfo_reqwidth())
        h = max(140, toast.winfo_reqheight())
        sw = toast.winfo_screenwidth()
        sh = toast.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        toast.geometry(f"{w}x{h}+{x}+{y}")

        toast.after(7000, lambda: toast.destroy() if toast.winfo_exists() else None)
    except Exception as err:
        print(f"Locked toast error: {err}")


def _generate_break_dashboard_image(current_work_seconds=0, display_width=860, display_height=260):
    """
    Generates EXACTLY 2 clean, modern, motivational charts in a sleek executive dark theme:
    1. Daily Consistency (Trend over recent weeks with 3h goal line)
    2. Cumulative Growth (Total deep work hours compounding over time)
    """
    if pd is None or plt is None or Image is None or mdates is None:
        return None

    log_path = _get_log_path()
    if not log_path.exists():
        events = []
    else:
        try:
            data = json.loads(log_path.read_text())
            events = data.get("events", [])
        except Exception:
            events = []

    if current_work_seconds > 0:
        events = list(events) + [{
            "sessionStartedAt": datetime.now().isoformat() + "Z",
            "workTimeSeconds": current_work_seconds,
            "breakTimeSeconds": 0,
            "productivityRating": 0,
            "workEndedBy": "timer",
        }]

    if not events:
        return None

    df = pd.DataFrame(events)
    df["started_at"] = pd.to_datetime(df["sessionStartedAt"], errors="coerce")
    df["date"] = df["started_at"].dt.date
    df["work_hours"] = df["workTimeSeconds"].fillna(df.get("workTimeMinutes", 0) * 60) / 3600

    daily_work = df.groupby("date")["work_hours"].sum().reset_index()
    daily_work["date"] = pd.to_datetime(daily_work["date"])
    daily_work = daily_work.sort_values("date")

    if daily_work.empty:
        return None

    plt.style.use("dark_background")
    fig = plt.figure(figsize=(9.6, 3.4), facecolor="#0F1626")
    fig.suptitle(
        "REAL-TIME FOCUS MOMENTUM & GROWTH",
        fontsize=10.5,
        fontweight="bold",
        color="#38BDF8",
        y=0.98,
    )

    # 1. Daily Focus Consistency (Left Chart)
    ax1 = fig.add_subplot(1, 2, 1, facecolor="#131E33")
    recent_daily = daily_work.tail(21)

    ax1.plot(
        recent_daily["date"],
        recent_daily["work_hours"],
        color="#38BDF8",
        linewidth=2.2,
        marker="o",
        markersize=3.5,
        label="Daily Focus",
    )
    ax1.fill_between(
        recent_daily["date"],
        recent_daily["work_hours"],
        color="#38BDF8",
        alpha=0.20,
    )
    ax1.axhline(
        3.0,
        color="#F59E0B",
        linestyle="--",
        linewidth=1.1,
        alpha=0.75,
        label="3h Daily Target",
    )
    ax1.set_title(
        "Daily Consistency (Recent Weeks)",
        fontsize=9.5,
        fontweight="bold",
        color="#E2E8F0",
        pad=5,
    )
    ax1.set_ylabel("Hours", color="#94A3B8", fontsize=7.5)
    ax1.grid(True, linestyle="--", alpha=0.18, color="#1E2B45")
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax1.tick_params(colors="#94A3B8", labelsize=7)
    ax1.legend(loc="upper left", frameon=False, fontsize=7)

    # 2. Cumulative Growth (Right Chart)
    ax2 = fig.add_subplot(1, 2, 2, facecolor="#131E33")
    daily_work["cumulative_hours"] = daily_work["work_hours"].cumsum()

    ax2.plot(
        daily_work["date"],
        daily_work["cumulative_hours"],
        color="#10B981",
        linewidth=2.4,
        label="Total Compounded",
    )
    ax2.fill_between(
        daily_work["date"],
        daily_work["cumulative_hours"],
        color="#10B981",
        alpha=0.20,
    )
    ax2.set_title(
        "Cumulative Deep Work Compounding",
        fontsize=9.5,
        fontweight="bold",
        color="#E2E8F0",
        pad=5,
    )
    ax2.set_ylabel("Total Hours", color="#94A3B8", fontsize=7.5)
    ax2.grid(True, linestyle="--", alpha=0.18, color="#1E2B45")
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax2.tick_params(colors="#94A3B8", labelsize=7)
    ax2.legend(loc="upper left", frameon=False, fontsize=7)

    total_hours = df["work_hours"].sum()
    total_sessions = len(df)
    stats_badge = f"TOTAL: {total_hours:.1f} hrs  •  SESSIONS: {total_sessions}  •  CONSISTENCY COMPOUNDS INTO MASTERY"
    fig.text(
        0.5,
        0.02,
        stats_badge,
        ha="center",
        fontsize=8,
        fontweight="bold",
        color="#38BDF8",
        bbox=dict(boxstyle="round,pad=0.25", facecolor="#131E33", edgecolor="#1E2B45"),
    )

    plt.tight_layout(rect=[0, 0.05, 1, 0.94])

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    img = Image.open(buf)
    img = img.resize((display_width, display_height), Image.Resampling.LANCZOS)
    return img


def _load_summary_stats(current_work_seconds=0):
    log_path = _get_log_path()
    if not log_path.exists():
        events = []
    else:
        try:
            data = json.loads(log_path.read_text())
            events = data.get("events", [])
        except Exception:
            events = []

    today_str = datetime.now().strftime("%Y-%m-%d")

    today_sessions = 0
    today_work_sec = current_work_seconds
    today_break_sec = 0
    today_ratings = []

    total_sessions = 0
    total_work_sec = current_work_seconds
    total_break_sec = 0
    total_ratings = []

    daily_work_seconds = {}
    end_reasons = {"timer": 0, "systemSleep": 0, "userBreakNow": 0, "other": 0}
    today_types = {"study": 0, "work": 0, "exercise": 0, "other": 0}

    for ev in events:
        if not isinstance(ev, dict):
            continue

        w_sec = ev.get("workTimeSeconds")
        if w_sec is None:
            w_sec = int(ev.get("workTimeMinutes", 0) * 60)

        b_sec = ev.get("breakTimeSeconds")
        if b_sec is None:
            b_sec = int(ev.get("breakTimeMinutes", 0) * 60)

        rating = ev.get("productivityRating", 0)
        ended_by = ev.get("workEndedBy", "other")
        if ended_by in end_reasons:
            end_reasons[ended_by] += 1
        else:
            end_reasons["other"] += 1

        total_sessions += 1
        total_work_sec += w_sec
        total_break_sec += b_sec
        if rating and rating > 0:
            total_ratings.append(rating)

        start_ts = ev.get("sessionStartedAt", "") or ev.get("sessionCompletedAt", "")
        event_date = ""
        if start_ts:
            try:
                dt = datetime.fromisoformat(start_ts.replace("Z", "+00:00"))
                event_date = dt.astimezone().strftime("%Y-%m-%d")
            except Exception:
                event_date = start_ts[:10]

        if event_date:
            daily_work_seconds[event_date] = daily_work_seconds.get(event_date, 0) + w_sec

        if event_date == today_str:
            today_sessions += 1
            today_work_sec += w_sec
            today_break_sec += b_sec
            if rating and rating > 0:
                today_ratings.append(rating)

            stypes = ev.get("sessionTypes")
            if not stypes:
                raw_stype = str(ev.get("sessionType", ev.get("activityType", "work"))).lower()
                stypes = [s.strip() for s in raw_stype.replace("+", ",").split(",") if s.strip()]
            for st in stypes:
                if st in today_types:
                    today_types[st] += 1
                else:
                    today_types["other"] += 1

    if current_work_seconds > 0:
        today_sessions += 1
        total_sessions += 1
        daily_work_seconds[today_str] = daily_work_seconds.get(today_str, 0) + current_work_seconds

    def format_duration(seconds):
        mins = int(round(seconds / 60))
        if mins < 60:
            return f"{mins}m"
        hrs = mins // 60
        rem_m = mins % 60
        if rem_m == 0:
            return f"{hrs}h"
        return f"{hrs}h {rem_m}m"

    # Calculate streak
    streak_count = 0
    if daily_work_seconds:
        dates_set = set(daily_work_seconds.keys())
        today_dt = datetime.now().date()
        check_dt = today_dt
        if check_dt.strftime("%Y-%m-%d") not in dates_set:
            check_dt = check_dt - timedelta(days=1)
        while check_dt.strftime("%Y-%m-%d") in dates_set:
            streak_count += 1
            check_dt = check_dt - timedelta(days=1)

    top_day_str = "N/A"
    if daily_work_seconds:
        top_date_key, max_sec = max(daily_work_seconds.items(), key=lambda x: x[1])
        try:
            formatted_date = datetime.strptime(top_date_key, "%Y-%m-%d").strftime("%b %d, %Y")
        except Exception:
            formatted_date = top_date_key
        top_day_str = f"{format_duration(max_sec)} ({formatted_date})"

    total_reasons_count = sum(end_reasons.values()) or 1
    timer_pct = round((end_reasons["timer"] / total_reasons_count) * 100, 1)
    sleep_pct = round((end_reasons["systemSleep"] / total_reasons_count) * 100, 1)

    today_avg = f"{sum(today_ratings)/len(today_ratings):.1f}★" if today_ratings else "N/A"
    total_avg = f"{sum(total_ratings)/len(total_ratings):.1f}★" if total_ratings else "N/A"

    today_mix_str = f"Today: 📚 {today_types['study']} Study  •  💼 {today_types['work']} Work  •  🏋️ {today_types['exercise']} Exercise"

    return {
        "today_sessions": today_sessions,
        "today_work": format_duration(today_work_sec),
        "today_break": format_duration(today_break_sec),
        "today_rating": today_avg,
        "total_sessions": total_sessions,
        "total_work": format_duration(total_work_sec),
        "total_rating": total_avg,
        "top_day": top_day_str,
        "streak_days": f"{streak_count} Days 🔥",
        "timer_pct": f"{timer_pct}%",
        "sleep_pct": f"{sleep_pct}%",
        "today_types": today_types,
        "today_mix": today_mix_str,
    }


def _render_text_stats_card(container, stats_data=None):
    import tkinter as tk
    if stats_data is None:
        stats_data = _load_summary_stats()

    stats_title_row = tk.Frame(container, bg="#0F1626")
    stats_title_row.pack(fill="x", pady=(0, 4))

    tk.Label(
        stats_title_row,
        text="⚡ LIVE PRODUCTIVITY METRICS",
        font=("Helvetica", 10, "bold"),
        fg="#F3F4F6",
        bg="#0F1626",
    ).pack(side="left")

    grid_frame = tk.Frame(container, bg="#0F1626")
    grid_frame.pack(fill="x")
    grid_frame.columnconfigure(0, weight=1)
    grid_frame.columnconfigure(1, weight=1)

    col1 = tk.Frame(grid_frame, bg="#131E33", padx=10, pady=8, highlightbackground="#1E2B45", highlightthickness=1)
    col1.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
    tk.Label(col1, text="📅 TODAY'S SPRINT", font=("Helvetica", 9, "bold"), fg="#38BDF8", bg="#131E33").pack(anchor="w", pady=(0, 2))
    tk.Label(col1, text=f"Sessions: {stats_data['today_sessions']}  |  Work: {stats_data['today_work']}", font=("Helvetica", 10, "bold"), fg="#F9FAFB", bg="#131E33").pack(anchor="w")

    col2 = tk.Frame(grid_frame, bg="#131E33", padx=10, pady=8, highlightbackground="#1E2B45", highlightthickness=1)
    col2.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
    tk.Label(col2, text="🚀 ALL-TIME MOMENTUM", font=("Helvetica", 9, "bold"), fg="#10B981", bg="#131E33").pack(anchor="w", pady=(0, 2))
    tk.Label(col2, text=f"Total: {stats_data['total_work']}  ({stats_data['total_sessions']} Sessions)", font=("Helvetica", 10, "bold"), fg="#F9FAFB", bg="#131E33").pack(anchor="w")


def _warn_headless_once(error):
    global _HEADLESS_WARNING_EMITTED
    if _HEADLESS_WARNING_EMITTED:
        return
    _HEADLESS_WARNING_EMITTED = True
    print(f"GUI unavailable ({error}); running headless.")


def _candidate_display_envs():
    displays = []
    current_display = os.environ.get("DISPLAY")
    if current_display:
        displays.append(current_display)

    for fallback_display in (":0", ":1"):
        if fallback_display not in displays:
            displays.append(fallback_display)

    xauthority_paths = []
    current_xauthority = os.environ.get("XAUTHORITY")
    if current_xauthority:
        xauthority_paths.append(Path(current_xauthority))

    home_xauthority = Path.home() / ".Xauthority"
    if home_xauthority.exists() and home_xauthority not in xauthority_paths:
        xauthority_paths.append(home_xauthority)

    runtime_dir = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    if runtime_dir.exists():
        for candidate in sorted(runtime_dir.glob("xauth_*")):
            if candidate not in xauthority_paths:
                xauthority_paths.append(candidate)

    if not xauthority_paths:
        xauthority_paths.append(Path.home() / ".Xauthority")

    for display in displays:
        for xauthority in xauthority_paths:
            yield display, xauthority


def _create_tk_root(window_title):
    import tkinter as tk

    if sys.platform == "win32":
        root = tk.Tk()
        root.title(window_title)
        return root

    last_error = None
    for display, xauthority in _candidate_display_envs():
        previous_display = os.environ.get("DISPLAY")
        previous_xauthority = os.environ.get("XAUTHORITY")

        os.environ["DISPLAY"] = display
        if xauthority:
            os.environ["XAUTHORITY"] = str(xauthority)

        try:
            root = tk.Tk()
            root.title(window_title)
            return root
        except Exception as error:
            last_error = error
            if previous_display is None:
                os.environ.pop("DISPLAY", None)
            else:
                os.environ["DISPLAY"] = previous_display

            if previous_xauthority is None:
                os.environ.pop("XAUTHORITY", None)
            else:
                os.environ["XAUTHORITY"] = previous_xauthority

    raise last_error


def _format_timer(seconds):
    minutes, rem = divmod(max(0, int(seconds)), 60)
    return f"{minutes:02d}:{rem:02d}"


def _sleep_gap_detected(previous_tick, current_tick, threshold_seconds=SUSPEND_GAP_SECONDS):
    return (current_tick - previous_tick) > max(1, int(threshold_seconds))


def _play_countdown_alert(root):
    try:
        root.bell()
    except Exception:
        pass
    try:
        print("\a", end="", flush=True)
    except Exception:
        pass


def play_beep():
    if sys.platform == "win32":
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
            return True
        except Exception:
            pass

    sound_files = [
        "/usr/share/sounds/freedesktop/stereo/bell.oga",
        "/usr/share/sounds/freedesktop/stereo/message.oga",
        "/usr/share/sounds/oxygen/stereo/dialog-information.ogg",
        "/usr/share/sounds/Oxygen-Sys-Special.ogg",
        "/usr/share/sounds/alsa/Front_Center.wav",
    ]

    for player in ["pw-play", "paplay", "aplay"]:
        for sound_file in sound_files:
            if Path(sound_file).exists():
                try:
                    subprocess.Popen([player, sound_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
                except Exception:
                    pass

    try:
        subprocess.Popen(["spd-say", "-t", "female1", "beep"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        pass

    def fallback_beeps():
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            root.bell()
            root.update()
            root.destroy()
        except Exception:
            pass
        try:
            print("\a", end="", flush=True)
        except Exception:
            pass

    import threading
    threading.Thread(target=fallback_beeps, daemon=True).start()
    return True


def wait_for_display(initial_delay_seconds=60, retry_seconds=60):
    initial_delay = max(0, int(initial_delay_seconds))
    retry_delay = max(1, int(retry_seconds))

    if initial_delay:
        print(f"Waiting {initial_delay}s before first GUI display check.")
        time.sleep(initial_delay)

    while True:
        try:
            root = _create_tk_root("Pomodoro Display Check")
            root.withdraw()
            root.update_idletasks()
            root.destroy()
            print("GUI display is available. Starting pomodoro cycles.")
            return True
        except ImportError:
            print("tkinter is unavailable; continuing in headless mode.")
            return False
        except Exception as error:
            print(f"Display unavailable ({error}); retrying in {retry_delay}s until display is ready.")
            time.sleep(retry_delay)


def _show_two_minute_warning_toast(root):
    """
    Shows an executive floating heads-up toast for 5 seconds with 2 minutes remaining so the user can conclude tasks smoothly.
    """
    import tkinter as tk

    if send_desktop_notification:
        send_desktop_notification(
            "⏳ Pomodoro: Break in 2 Minutes",
            "Wrap up and save your work. 2 minutes remaining before break starts.",
            urgency="critical",
        )
    else:
        try:
            subprocess.Popen(
                ["notify-send", "-u", "critical", "-t", "5000", "⏳ Pomodoro: Break in 2 Minutes", "Wrap up and conclude your current thought before break starts."],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    try:
        toast = tk.Toplevel(root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg="#F59E0B")

        card = tk.Frame(toast, bg="#0E1626", padx=24, pady=12)
        card.pack(padx=2, pady=2, fill="both", expand=True)

        tk.Label(
            card,
            text="⏳ BREAK IN 2 MINUTES",
            font=("Helvetica", 14, "bold"),
            fg="#F59E0B",
            bg="#0E1626",
        ).pack()

        tk.Label(
            card,
            text="Conclude your current thought & save your work — 2 minutes remaining to wrap up.",
            font=("Helvetica", 10),
            fg="#CBD5E1",
            bg="#0E1626",
        ).pack(pady=(4, 0))

        toast.update_idletasks()
        w = max(440, toast.winfo_reqwidth())
        h = max(75, toast.winfo_reqheight())
        sw = toast.winfo_screenwidth()
        x = max(0, (sw - w) // 2)
        y = 35
        toast.geometry(f"{w}x{h}+{x}+{y}")

        toast.after(5000, lambda: toast.destroy() if toast.winfo_exists() else None)
    except Exception as err:
        print(f"2-min warning toast error: {err}")


def run_work_session(work_seconds):
    try:
        root = _create_tk_root("Pomodoro Work Session")
    except ImportError:
        print("tkinter is unavailable; work session canceled because GUI is required.")
        return {
            "plannedWorkSeconds": work_seconds,
            "actualWorkSeconds": 0,
            "workEndedBy": "guiUnavailable",
            "interactionLog": [],
            "guiAvailable": False,
            "sessionCanceled": True,
        }
    except Exception as error:
        _warn_headless_once(error)
        print("Work session canceled because GUI is required.")
        return {
            "plannedWorkSeconds": work_seconds,
            "actualWorkSeconds": 0,
            "workEndedBy": "guiUnavailable",
            "interactionLog": [],
            "guiAvailable": False,
            "sessionCanceled": True,
        }
    import tkinter as tk

    root.attributes("-topmost", False)
    root.geometry("740x440")
    root.iconify()
    root.configure(bg="#070A11")

    started_at = time.time()
    last_tick_at = started_at
    state = {
        "remaining": max(MIN_DURATION_SECONDS, int(work_seconds)),
        "go_break_now": False,
        "interaction_log": [],
        "suspend_detected": False,
        "active_elapsed_seconds": 0,
        "warning_2min_shown": False,
    }

    title_label = tk.Label(
        root,
        text="Deep Work Session",
        font=("Helvetica", 26, "bold"),
        fg="#F8FAFC",
        bg="#070A11",
    )
    title_label.pack(pady=(16, 8))

    # Live system metrics badge in work window
    sys_lbl = tk.Label(
        root,
        text="💻 System: Checking resources...",
        font=("Helvetica", 10),
        fg="#64748B",
        bg="#070A11",
    )
    sys_lbl.pack(pady=(0, 10))

    timer_label = tk.Label(
        root,
        text=_format_timer(state["remaining"]),
        font=("Helvetica", 72, "bold"),
        fg="#38BDF8",
        bg="#070A11",
    )
    timer_label.pack(pady=10)

    message_label = tk.Label(
        root,
        text="Laser Focus Mode • Minimize distractions & execute.",
        font=("Helvetica", 13),
        fg="#94A3B8",
        bg="#070A11",
    )
    message_label.pack(pady=10)

    skips_left, skips_used = _get_skips_remaining(max_skips=MAX_DAILY_SKIPS)

    def go_on_break_now():
        if state["go_break_now"]:
            return
        left, used = _get_skips_remaining(max_skips=MAX_DAILY_SKIPS)
        if state["remaining"] > 0:
            if left <= 0:
                _show_locked_warning_toast(root, "You have reached the limit and now nothing can be done after this. You have to wait.")
                return
            _record_daily_skip("work_early_break")
            state["interaction_log"].append({"event": "usedDailySkipWork", "at": int(time.time() - started_at)})

        state["go_break_now"] = True
        state["interaction_log"].append({"event": "goBreakNow", "at": int(time.time() - started_at)})

    btn_txt = f"Go On Break Now ({skips_left}/2 Skips Left)" if skips_left > 0 else "🔒 Locked (Daily Skip Limit 2/2 Reached)"
    btn_bg = "#F59E0B" if skips_left > 0 else "#1E293B"
    btn_fg = "#070A11" if skips_left > 0 else "#64748B"
    btn_state = "normal" if skips_left > 0 else "disabled"

    action_button = tk.Button(
        root,
        text=btn_txt,
        font=("Helvetica", 13, "bold"),
        bg=btn_bg,
        fg=btn_fg,
        state=btn_state,
        relief="flat",
        bd=0,
        cursor="hand2" if skips_left > 0 else "",
        padx=20,
        pady=8,
        command=go_on_break_now,
    )
    action_button.pack(pady=14)

    loop_count = 0
    last_tick_at = time.time()
    while state["remaining"] > 0 and not state["go_break_now"]:
        try:
            if not root.winfo_exists():
                break
        except Exception:
            break

        try:
            timer_label.config(text=_format_timer(state["remaining"]))

            # Periodic live system metrics update
            loop_count += 1
            if get_system_metrics and loop_count % 2 == 0:
                metrics = get_system_metrics()
                if metrics["is_high_usage"]:
                    sys_lbl.config(
                        text=f"⚠️ HIGH SYSTEM USAGE: CPU {metrics['cpu_percent']:.0f}%  •  RAM {metrics['memory_percent']:.0f}% ({metrics['memory_used_gb']:.1f}/{metrics['memory_total_gb']:.1f} GB) — Close heavy apps",
                        fg="#EF4444",
                    )
                else:
                    sys_lbl.config(
                        text=f"💻 System: CPU {metrics['cpu_percent']:.0f}%  •  RAM {metrics['memory_percent']:.0f}% ({metrics['memory_used_gb']:.1f}/{metrics['memory_total_gb']:.1f} GB)  •  🌐 Net: {metrics['network_status']}",
                        fg="#64748B",
                    )

            root.update()
        except Exception:
            break

        if state["remaining"] <= 3:
            _play_countdown_alert(root)
        elif state["remaining"] <= WARNING_SECONDS and not state["warning_2min_shown"]:
            state["warning_2min_shown"] = True
            play_beep()
            _show_two_minute_warning_toast(root)
            try:
                if root.winfo_exists():
                    message_label.config(
                        text="⏳ 2 Minutes Remaining: Conclude your current thought & save work for the break.",
                        fg="#F59E0B",
                    )
            except Exception:
                pass

        tick_before_sleep = time.time()
        time.sleep(1)
        tick_after_sleep = time.time()
        if _sleep_gap_detected(last_tick_at, tick_after_sleep):
            state["suspend_detected"] = True
            break

        state["remaining"] -= 1
        state["active_elapsed_seconds"] += max(1, int(round(tick_after_sleep - tick_before_sleep)))
        last_tick_at = tick_after_sleep

    actual_work_seconds = state["active_elapsed_seconds"] or int(time.time() - started_at)
    if state["suspend_detected"]:
        ended_by = "systemSleep"
    else:
        ended_by = "userBreakNow" if state["go_break_now"] else "timer"

    if not state["suspend_detected"]:
        play_beep()

    try:
        if root.winfo_exists():
            root.destroy()
    except Exception:
        pass

    return {
        "plannedWorkSeconds": max(MIN_DURATION_SECONDS, int(work_seconds)),
        "actualWorkSeconds": max(1, actual_work_seconds),
        "workEndedBy": ended_by,
        "sessionNote": "",
        "interactionLog": state["interaction_log"],
        "guiAvailable": True,
        "sessionInterruptedBySleep": state["suspend_detected"],
    }


def run_break_session(
    break_seconds,
    default_next_work_seconds,
    default_next_break_seconds,
    stats=None,
    is_walk_break=False,
    session_number=1,
):
    """
    Modern Executive Break Dashboard:
    - Sleek dark theme (#070A11) with elevated cards and glowing accents.
    - 2 motivational charts only (Daily Consistency & Cumulative Compounding).
    - Time-based routine checklist with active step highlighting.
    - Multi-select session activity tags (📚 Study, 💼 Work, 🏋️ Exercise, 🎯 Other).
    - Mandatory session time presets (25m, 30m, 40m, 50m, 60m).
    - Mandatory 1-5 Star focus rating before resuming.
    """
    try:
        root = _create_tk_root("Pomodoro Break Session")
    except ImportError:
        print("tkinter is unavailable; break session canceled because GUI is required.")
        return {
            "plannedBreakSeconds": break_seconds,
            "actualBreakSeconds": 0,
            "breakEndedBy": "guiUnavailable",
            "nextWorkSeconds": default_next_work_seconds,
            "nextBreakSeconds": default_next_break_seconds,
            "interactionLog": [],
            "productivityRating": None,
            "sessionTypes": ["work"],
            "sessionType": "work",
            "routineSelected": "nothing",
            "exitApp": False,
            "sessionCanceled": True,
            "guiAvailable": False,
        }
    except Exception as error:
        _warn_headless_once(error)
        print("Break session canceled because GUI is required.")
        return {
            "plannedBreakSeconds": break_seconds,
            "actualBreakSeconds": 0,
            "breakEndedBy": "guiUnavailable",
            "nextWorkSeconds": default_next_work_seconds,
            "nextBreakSeconds": default_next_break_seconds,
            "interactionLog": [],
            "productivityRating": None,
            "sessionTypes": ["work"],
            "sessionType": "work",
            "routineSelected": "nothing",
            "exitApp": False,
            "sessionCanceled": True,
            "guiAvailable": False,
        }
    import tkinter as tk

    root.update_idletasks()
    sw = 1280
    sh = 800
    try:
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        root.geometry(f"{sw}x{sh}+0+0")
    except Exception:
        pass
    try:
        root.attributes("-fullscreen", True)
    except Exception:
        pass
    try:
        root.overrideredirect(True)
    except Exception:
        pass
    root.configure(bg="#070A11")

    try:
        root.attributes("-topmost", True)
        root.lift()
        root.focus_force()
    except Exception:
        pass

    try:
        root.grab_set_global()
    except Exception:
        try:
            root.grab_set()
        except Exception:
            pass

    started_at = time.time()
    last_tick_at = started_at
    state = {
        "remaining": max(MIN_DURATION_SECONDS, int(break_seconds)),
        "end_break_now": False,
        "exit_app": False,
        "next_work": max(MIN_DURATION_SECONDS, int(default_next_work_seconds)),
        "next_break": max(MIN_DURATION_SECONDS, int(default_next_break_seconds)),
        "interaction_log": [],
        "productivity_rating": 4,
        "session_types": {"work"},
        "session_time_selected": False,
        "suspend_detected": False,
        "active_elapsed_seconds": 0,
        "beep_20sec_played": False,
        "session_note": "",
        "routine_selected": "nothing",
    }
    ui_callbacks = {}
    custom_entry = None

    def validate_mandatory_inputs():
        if not state["session_types"]:
            state["session_types"] = {"work"}
        if state["productivity_rating"] is None:
            state["productivity_rating"] = 4
        if not state.get("routine_selected"):
            state["routine_selected"] = "nothing"
        return True

    def end_break_now():
        validate_mandatory_inputs()
        # If break timer is still running, this counts as an early skip!
        if state["remaining"] > 0:
            left, used = _get_skips_remaining(max_skips=MAX_DAILY_SKIPS)
            if left <= 0:
                _show_locked_warning_toast(root, "You have reached the limit and now nothing can be done after this. You have to wait.")
                return
            _record_daily_skip("break_early_continue")
            state["interaction_log"].append({"event": "usedDailySkipBreak", "skipsUsed": used + 1, "at": int(time.time() - started_at)})

        if state["end_break_now"]:
            return
        state["end_break_now"] = True
        state["interaction_log"].append({"event": "endBreakNow", "at": int(time.time() - started_at)})

    def exit_app():
        validate_mandatory_inputs()
        if state["exit_app"]:
            return
        state["exit_app"] = True
        state["interaction_log"].append({"event": "exitApp", "at": int(time.time() - started_at)})

    # Universal fail-safe keyboard shortcuts on root
    root.bind("<Escape>", lambda e: exit_app())
    root.bind("<Control-q>", lambda e: exit_app())
    root.bind("<Control-Q>", lambda e: exit_app())
    root.bind("<Control-c>", lambda e: exit_app())
    root.bind("<Control-C>", lambda e: exit_app())

    def on_enter_pressed(event=None):
        try:
            focused = root.focus_get()
            if custom_entry and focused == custom_entry:
                return
        except Exception:
            pass
        end_break_now()

    root.bind("<Return>", on_enter_pressed)
    root.bind("<KP_Enter>", on_enter_pressed)

    # Central layout container
    main_frame = tk.Frame(root, bg="#070A11")
    main_frame.pack(expand=True, fill="both", padx=28, pady=10)

    # 1. ACTION FOOTER BAR (Pack side="bottom" FIRST to guarantee it is always on-screen regardless of scaling/resolution)
    footer_frame = tk.Frame(main_frame, bg="#070A11")
    footer_frame.pack(side="bottom", fill="x", pady=(8, 0))

    footer_center = tk.Frame(footer_frame, bg="#070A11")
    footer_center.pack(anchor="center")

    skips_left_init, _ = _get_skips_remaining(max_skips=MAX_DAILY_SKIPS)
    resume_btn_text = f"( ⚡ RESUME WORK EARLY • {skips_left_init}/2 Skips Left [Enter] )" if skips_left_init > 0 else "( 🔒 LOCKED: SKIP LIMIT REACHED (2/2) — YOU HAVE TO WAIT )"
    resume_btn_bg = "#065F46" if skips_left_init > 0 else "#1E293B"
    resume_btn_fg = "#A7F3D0" if skips_left_init > 0 else "#EF4444"
    resume_btn_state = "normal" if skips_left_init > 0 else "disabled"
    resume_btn_cursor = "hand2" if skips_left_init > 0 else ""

    resume_btn = tk.Button(
        footer_center,
        text=resume_btn_text,
        font=("Helvetica", 13, "bold"),
        bg=resume_btn_bg,
        fg=resume_btn_fg,
        state=resume_btn_state,
        cursor=resume_btn_cursor,
        activebackground="#34D399",
        activeforeground="#020617",
        relief="flat",
        bd=0,
        padx=32,
        pady=10,
        command=end_break_now,
    )
    resume_btn.pack(side="left", padx=12)

    exit_btn = tk.Button(
        footer_center,
        text="( 🔴 EXIT APP [Esc] )",
        font=("Helvetica", 13, "bold"),
        bg="#DC2626",
        fg="#FFFFFF",
        activebackground="#991B1B",
        activeforeground="#FFFFFF",
        relief="flat",
        bd=0,
        cursor="hand2",
        padx=28,
        pady=10,
        command=exit_app,
    )
    exit_btn.pack(side="left", padx=12)

    def update_resume_state():
        if resume_btn is None:
            return
        skips_left, skips_used = _get_skips_remaining(max_skips=MAX_DAILY_SKIPS)
        if state["remaining"] > 0:
            if skips_left <= 0:
                resume_btn.config(
                    bg="#1E293B",
                    fg="#EF4444",
                    text="( 🔒 LOCKED: SKIP LIMIT REACHED (2/2) — YOU HAVE TO WAIT )",
                    state="disabled",
                    cursor="",
                )
            else:
                resume_btn.config(
                    bg="#065F46",
                    fg="#A7F3D0",
                    text=f"( ⚡ RESUME WORK EARLY • {skips_left}/2 Skips Left [Enter] )",
                    state="normal",
                    cursor="hand2",
                )
        else:
            resume_btn.config(
                bg="#10B981",
                fg="#020617",
                text="( ⚡ RESUME NEXT WORK SESSION [Enter] • BREAK COMPLETE ✓ )",
                state="normal",
                cursor="hand2",
            )

    # 2. UNIFIED LAUNCHPAD CARD (Pack side="bottom" ABOVE footer_frame)
    launchpad_card = tk.Frame(main_frame, bg="#0F172A", highlightbackground="#334155", highlightthickness=2, padx=20, pady=8)
    launchpad_card.pack(side="bottom", fill="x", pady=(0, 6))

    # 3. TOP HEADER APP BAR (Pack side="top")
    app_bar = tk.Frame(main_frame, bg="#0F172A", highlightbackground="#334155", highlightthickness=2, padx=20, pady=8)
    app_bar.pack(side="top", fill="x", pady=(0, 6))

    hdr_title = f"☕ RECHARGE & DEEP RESET  •  SESSION #{session_number} COMPLETE"
    hdr_color = "#38BDF8"
    hdr_sub = "Cognitive Integration Break • 4-Minute Reset — Rest your eyes, stretch, hydrate, and reset mental clarity."

    title_box = tk.Frame(app_bar, bg="#0F172A")
    title_box.pack(side="left")

    tk.Label(title_box, text=hdr_title, font=("Helvetica", 15, "bold"), fg=hdr_color, bg="#0F172A").pack(anchor="w")
    tk.Label(title_box, text=hdr_sub, font=("Helvetica", 10), fg="#94A3B8", bg="#0F172A").pack(anchor="w", pady=(2, 0))

    badge_box = tk.Frame(app_bar, bg="#0F172A")
    badge_box.pack(side="right")

    tk.Button(
        badge_box,
        text="✕ Exit (Esc)",
        font=("Helvetica", 10, "bold"),
        bg="#7F1D1D",
        fg="#FCA5A5",
        activebackground="#991B1B",
        activeforeground="#FFFFFF",
        relief="flat",
        bd=0,
        cursor="hand2",
        padx=12,
        pady=4,
        command=exit_app,
    ).pack(side="right", padx=(8, 0))

    streak_text = stats.get("streak_days", "3 Days 🔥") if stats else "Focus Active"
    tk.Label(
        badge_box,
        text=f"🔥 {streak_text}",
        font=("Helvetica", 11, "bold"),
        fg="#F59E0B",
        bg="#1E293B",
        padx=12,
        pady=5,
        highlightbackground="#F59E0B",
        highlightthickness=1,
    ).pack(side="right", padx=(8, 0))

    # Live system metrics badge in break app bar
    sys_perf_lbl = tk.Label(
        badge_box,
        text="💻 Checking resources...",
        font=("Helvetica", 10, "bold"),
        fg="#94A3B8",
        bg="#1E293B",
        padx=12,
        pady=5,
        highlightbackground="#334155",
        highlightthickness=1,
    )
    sys_perf_lbl.pack(side="right", padx=(0, 6))

    # 4. MOTIVATIONAL QUOTE CARD (Pack side="top")
    quote_card = tk.Frame(main_frame, bg="#111827", highlightbackground="#374151", highlightthickness=2, padx=18, pady=6)
    quote_card.pack(side="top", fill="x", pady=(0, 6))

    selected_quote = random.choice(MOTIVATIONAL_QUOTES)
    tk.Label(
        quote_card,
        text=f'💡  "{selected_quote}"',
        font=("Helvetica", 13, "bold"),
        fg="#F9FAFB",
        bg="#111827",
    ).pack(pady=1)

    # 5. HERO TIMER CARD (Pack side="top")
    timer_hero = tk.Frame(main_frame, bg="#0F172A", highlightbackground="#334155", highlightthickness=2, padx=18, pady=6)
    timer_hero.pack(side="top", fill="x", pady=(0, 6))

    timer_color = "#38BDF8"
    timer_label = tk.Label(
        timer_hero,
        text=_format_timer(state["remaining"]),
        font=("Helvetica", 54, "bold"),
        fg=timer_color,
        bg="#0F172A",
    )
    timer_label.pack()

    timer_status_badge = tk.Label(
        timer_hero,
        text="🟢 BREAK TIMER RUNNING  •  STAND UP, STRETCH & RELAX YOUR EYES",
        font=("Helvetica", 11, "bold"),
        fg="#10B981",
        bg="#0F172A",
    )
    timer_status_badge.pack(pady=(1, 3))

    # 6. DAILY SKIP LIMIT & LOCK STATUS CARD (Pack side="top")
    skips_left, skips_used = _get_skips_remaining(max_skips=MAX_DAILY_SKIPS)
    skip_card_bg = "#450A0A" if skips_left <= 0 else "#0F172A"
    skip_border = "#EF4444" if skips_left <= 0 else "#334155"

    skip_status_card = tk.Frame(
        main_frame,
        bg=skip_card_bg,
        highlightbackground=skip_border,
        highlightthickness=2,
        padx=18,
        pady=6,
    )
    skip_status_card.pack(side="top", fill="x", pady=(0, 6))

    skip_status_lbl = tk.Label(
        skip_status_card,
        text=f"⚡ DAILY EARLY CONTINUES / SKIPS: {skips_left} OF 2 REMAINING TODAY" if skips_left > 0 else "🔒 DAILY SKIP LIMIT REACHED (2/2 USED) • SCREEN LOCKED UNTIL TIMER COMPLETES",
        font=("Helvetica", 10, "bold"),
        fg="#38BDF8" if skips_left > 0 else "#FCA5A5",
        bg=skip_card_bg,
    )
    skip_status_lbl.pack(side="left")

    skip_limit_msg_lbl = tk.Label(
        skip_status_card,
        text="🔒 You have reached the limit and now nothing can be done after this. You have to wait.",
        font=("Helvetica", 10, "bold"),
        fg="#FCA5A5",
        bg=skip_card_bg,
    )
    if skips_left <= 0:
        skip_limit_msg_lbl.pack(side="right")

    # 7. MIDDLE SPLIT: 2 Motivational Charts (Left) & Habit Routine Checklist (Right)
    mid_container = tk.Frame(main_frame, bg="#070A11")
    mid_container.pack(side="top", fill="both", expand=True, pady=(0, 6))
    mid_container.columnconfigure(0, weight=6)
    mid_container.columnconfigure(1, weight=5)

    # 2-CHART CONTAINER (Left Column)
    chart_col = tk.Frame(mid_container, bg="#0F172A", highlightbackground="#334155", highlightthickness=2, padx=6, pady=6)
    chart_col.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

    target_chart_w = max(420, min(750, int(sw * 0.52)))
    target_chart_h = max(130, min(200, int(sh * 0.22)))

    try:
        raw_dash_img = _generate_break_dashboard_image(
            current_work_seconds=0,
            display_width=target_chart_w,
            display_height=target_chart_h,
        )
        if raw_dash_img:
            state["dashboard_photo"] = ImageTk.PhotoImage(raw_dash_img, master=root)
            chart_lbl = tk.Label(chart_col, image=state["dashboard_photo"], bg="#0F172A")
            chart_lbl.pack(expand=True, fill="both")
        else:
            _render_text_stats_card(chart_col, stats)
    except Exception as img_err:
        print(f"Chart render error: {img_err}")
        try:
            if root.winfo_exists():
                _render_text_stats_card(chart_col, stats)
        except Exception:
            pass

    # TIME-BASED ROUTINE CHECKLIST (Right Column)
    routine_col = tk.Frame(mid_container, bg="#0F172A", highlightbackground="#334155", highlightthickness=2, padx=20, pady=12)
    routine_col.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

    time_slot = _get_time_slot()
    slot_info = DEFAULT_ROUTINE_SCHEDULE.get(time_slot, DEFAULT_ROUTINE_SCHEDULE["morning"])

    r_hdr = tk.Frame(routine_col, bg="#0F172A")
    r_hdr.pack(fill="x", pady=(0, 6))

    tk.Label(
        r_hdr,
        text=slot_info["name"],
        font=("Helvetica", 12, "bold"),
        fg="#38BDF8",
        bg="#0F172A",
    ).pack(side="left")

    def select_routine_nothing():
        state["routine_selected"] = "nothing"
        nothing_btn.config(
            text="( ✓ Nothing Selected )",
            bg="#475569",
            fg="#F8FAFC",
            font=("Helvetica", 10, "bold"),
        )
        status_lbl.config(text="✓ Routine: Nothing / Skipped for this break", fg="#94A3B8")
        state["interaction_log"].append({"event": "selectRoutineNothing", "at": int(time.time() - started_at)})
        update_resume_state()

    nothing_btn = tk.Button(
        r_hdr,
        text="( ❌ Nothing )",
        font=("Helvetica", 10, "bold"),
        bg="#1E293B",
        fg="#CBD5E1",
        activebackground="#475569",
        activeforeground="#FFFFFF",
        relief="flat",
        bd=0,
        cursor="hand2",
        padx=14,
        pady=3,
        command=select_routine_nothing,
    )
    nothing_btn.pack(side="right")

    status_lbl = tk.Label(
        routine_col,
        text="💡 Wellness & Routine Habits (Optional — click Done if completed)",
        font=("Helvetica", 10, "bold"),
        fg="#38BDF8",
        bg="#0F172A",
        anchor="w",
    )
    status_lbl.pack(fill="x", pady=(0, 6))

    completed_records = _load_routine_completions()
    completed_task_ids = {c.get("taskId") for c in completed_records}
    routine_tasks = list(slot_info["tasks"])

    tasks_box = tk.Frame(routine_col, bg="#0F172A")
    tasks_box.pack(fill="both", expand=True)

    def refresh_task_list_ui():
        for widget in tasks_box.winfo_children():
            widget.destroy()

        active_task = None
        for t in routine_tasks:
            if t["id"] not in completed_task_ids:
                active_task = t
                break

        if state.get("routine_selected") == "nothing":
            status_lbl.config(text="✓ Routine: Nothing / Skipped for this break", fg="#94A3B8")
        elif state.get("routine_selected"):
            status_lbl.config(text="✓ Routine task completed & confirmed!", fg="#10B981")
        elif active_task is None:
            state["routine_selected"] = "all_completed"
            status_lbl.config(
                text="🎉 All routine tasks for this period completed & logged!",
                fg="#10B981",
            )
        else:
            status_lbl.config(
                text=f"👉 Active Target: {active_task['title']}  •  (Or click 'Nothing')",
                fg="#FBBF24",
            )

        for t in routine_tasks:
            is_done = t["id"] in completed_task_ids
            is_active = (active_task and active_task["id"] == t["id"])

            row_bg = "#1E293B" if is_active else "#0F172A"
            row = tk.Frame(
                tasks_box,
                bg=row_bg,
                padx=10,
                pady=6,
                highlightbackground="#38BDF8" if is_active else "#1E293B",
                highlightthickness=1,
            )
            row.pack(fill="x", pady=2.5)

            check_icon = "✓" if is_done else "○"
            check_fg = "#10B981" if is_done else "#64748B"
            tk.Label(
                row,
                text=f"[{check_icon}]",
                font=("Helvetica", 12, "bold"),
                fg=check_fg,
                bg=row_bg,
                width=3,
            ).pack(side="left")

            title_fg = "#64748B" if is_done else ("#F8FAFC" if is_active else "#CBD5E1")
            title_font = ("Helvetica", 11, "bold") if is_active else ("Helvetica", 11)
            tk.Label(
                row,
                text=t["title"],
                font=title_font,
                fg=title_fg,
                bg=row_bg,
            ).pack(side="left", padx=8)

            def mark_task_ok(tid=t["id"], title=t["title"]):
                completed_task_ids.add(tid)
                _save_routine_completion(tid, title)
                play_beep()
                state["routine_selected"] = tid
                if nothing_btn:
                    nothing_btn.config(text="( ❌ Nothing )", bg="#1E293B", fg="#CBD5E1", font=("Helvetica", 10))
                state["interaction_log"].append({"event": "completeRoutineTask", "taskId": tid, "at": int(time.time() - started_at)})
                refresh_task_list_ui()
                update_resume_state()

            if not is_done:
                btn_bg = "#10B981" if is_active else "#1E293B"
                btn_fg = "#020617" if is_active else "#CBD5E1"
                tk.Button(
                    row,
                    text="( ✓ Done )",
                    font=("Helvetica", 10, "bold"),
                    bg=btn_bg,
                    fg=btn_fg,
                    activebackground="#34D399",
                    activeforeground="#020617",
                    relief="flat",
                    bd=0,
                    cursor="hand2",
                    padx=14,
                    pady=4,
                    command=mark_task_ok,
                ).pack(side="right")
            else:
                tk.Label(
                    row,
                    text="Completed ✓",
                    font=("Helvetica", 10, "bold"),
                    fg="#10B981",
                    bg=row_bg,
                ).pack(side="right", padx=10)

    refresh_task_list_ui()

    quick_add_frame = tk.Frame(routine_col, bg="#0F172A")
    quick_add_frame.pack(fill="x", pady=(8, 0))

    def drink_water_quick():
        wid = f"water_glass_{int(time.time())}"
        wtitle = "💧 Drank a glass of fresh water"
        completed_task_ids.add(wid)
        _save_routine_completion(wid, wtitle)
        play_beep()
        state["routine_selected"] = wid
        if nothing_btn:
            nothing_btn.config(text="( ❌ Nothing )", bg="#1E293B", fg="#CBD5E1", font=("Helvetica", 10))
        routine_tasks.append({"id": wid, "title": wtitle, "desc": "Hydration recorded."})
        refresh_task_list_ui()
        update_resume_state()

    def flash_routine_warning():
        routine_col.config(highlightbackground="#DC2626")
        status_lbl.config(text="⚠️ MANDATORY: Check a task as Done or click '( ❌ Nothing )'!", fg="#EF4444")
        if nothing_btn:
            nothing_btn.config(bg="#DC2626", fg="#FFFFFF")

        def reset_routine_ui():
            routine_col.config(highlightbackground="#334155")
            if state.get("routine_selected") == "nothing":
                if nothing_btn:
                    nothing_btn.config(text="( ✓ Nothing Selected )", bg="#475569", fg="#F8FAFC", font=("Helvetica", 10, "bold"))
                status_lbl.config(text="✓ Routine: Nothing / Skipped for this break", fg="#94A3B8")
            elif state.get("routine_selected"):
                if nothing_btn:
                    nothing_btn.config(text="( ❌ Nothing )", bg="#1E293B", fg="#CBD5E1", font=("Helvetica", 10))
                status_lbl.config(text="✓ Routine task completed & confirmed!", fg="#10B981")
            else:
                if nothing_btn:
                    nothing_btn.config(text="( ❌ Nothing )", bg="#1E293B", fg="#CBD5E1", font=("Helvetica", 10))
                refresh_task_list_ui()

        root.after(700, reset_routine_ui)

    tk.Button(
        quick_add_frame,
        text="( 💧 Drink Water +1 Cup )",
        font=("Helvetica", 10, "bold"),
        bg="#0284C7",
        fg="#F0F9FF",
        activebackground="#38BDF8",
        activeforeground="#020617",
        relief="flat",
        bd=0,
        cursor="hand2",
        padx=14,
        pady=5,
        command=drink_water_quick,
    ).pack(side="left")

    custom_entry = tk.Entry(
        quick_add_frame,
        font=("Helvetica", 10),
        bg="#1E293B",
        fg="#F8FAFC",
        insertbackground="#38BDF8",
        relief="flat",
        highlightbackground="#334155",
        highlightthickness=1,
        width=20,
    )
    custom_entry.pack(side="left", padx=8, ipady=4)
    custom_entry.insert(0, "Add checklist task...")

    def on_entry_focus(e):
        if custom_entry.get() == "Add checklist task...":
            custom_entry.delete(0, "end")

    custom_entry.bind("<FocusIn>", on_entry_focus)

    def add_custom_task(event=None):
        txt = custom_entry.get().strip()
        if txt and txt != "Add checklist task...":
            cid = f"custom_{int(time.time())}"
            routine_tasks.append({"id": cid, "title": f"📌 {txt}", "desc": "Custom user task."})
            custom_entry.delete(0, "end")
            refresh_task_list_ui()

    custom_entry.bind("<Return>", add_custom_task)
    tk.Button(
        quick_add_frame,
        text="( + Add )",
        font=("Helvetica", 10, "bold"),
        bg="#334155",
        fg="#F8FAFC",
        activebackground="#475569",
        relief="flat",
        bd=0,
        cursor="hand2",
        padx=12,
        pady=5,
        command=add_custom_task,
    ).pack(side="left")

    lp_hdr = tk.Frame(launchpad_card, bg="#0F172A")
    lp_hdr.pack(fill="x", pady=(0, 6))

    tk.Label(
        lp_hdr,
        text="🚀 NEXT SPRINT CONFIGURATION",
        font=("Helvetica", 12, "bold"),
        fg="#F8FAFC",
        bg="#0F172A",
    ).pack(side="left")

    today_mix_text = stats.get("today_mix", "") if stats else ""
    if not today_mix_text:
        today_mix_text = "Track: 📚 Study • 💼 Work • 🏋️ Exercise"
    tk.Label(
        lp_hdr,
        text=today_mix_text,
        font=("Helvetica", 10, "bold"),
        fg="#38BDF8",
        bg="#0F172A",
    ).pack(side="right")

    # SECTION 1: SPRINT DURATION (OPTIONAL / CUSTOMIZABLE PRESETS)
    row1 = tk.Frame(launchpad_card, bg="#0F172A")
    row1.pack(fill="x", pady=6)

    tk.Label(row1, text="⏱️ SPRINT DURATION:", font=("Helvetica", 12, "bold"), fg="#94A3B8", bg="#0F172A", width=20, anchor="w").pack(side="left")

    current_mins = int(round(state["next_work"] / 60))
    time_status_lbl = tk.Label(
        row1,
        text=f"Current: {current_mins}m (Optional Preset)",
        font=("Helvetica", 11, "bold"),
        fg="#38BDF8",
        bg="#0F172A",
        width=34,
        anchor="e",
    )
    time_status_lbl.pack(side="right")

    time_btn_frame = tk.Frame(row1, bg="#0F172A")
    time_btn_frame.pack(side="left", padx=4)

    time_presets = [25, 30, 40, 50, 60]
    time_preset_buttons = {}

    def set_session_time(minutes):
        state["next_work"] = minutes * 60
        state["session_time_selected"] = True
        next_work_label.config(text=_format_timer(state["next_work"]))
        time_status_lbl.config(text=f"Duration: {minutes}m (Active ✓)", fg="#10B981")
        for m, btn in time_preset_buttons.items():
            if m == minutes:
                btn.config(text=f"( ✓ {m}m )", bg="#06B6D4", fg="#020617", font=("Helvetica", 11, "bold"))
            else:
                btn.config(text=f"( {m}m )", bg="#1E293B", fg="#CBD5E1", font=("Helvetica", 11))
        state["interaction_log"].append({
            "event": "selectNextWorkPreset",
            "minutes": minutes,
            "at": int(time.time() - started_at),
        })
        update_resume_state()

    for m in time_presets:
        is_default = (m == current_mins)
        btn_txt = f"( ✓ {m}m )" if is_default else f"( {m}m )"
        btn_bg = "#06B6D4" if is_default else "#1E293B"
        btn_fg = "#020617" if is_default else "#CBD5E1"
        btn = tk.Button(
            time_btn_frame,
            text=btn_txt,
            font=("Helvetica", 11, "bold" if is_default else "normal"),
            bg=btn_bg,
            fg=btn_fg,
            activebackground="#06B6D4",
            activeforeground="#020617",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=16,
            pady=5,
            command=lambda mins=m: set_session_time(mins),
        )
        btn.pack(side="left", padx=4)
        time_preset_buttons[m] = btn

    tk.Label(time_btn_frame, text=" | ", font=("Helvetica", 11), fg="#475569", bg="#0F172A").pack(side="left", padx=4)

    def adjust_next_work(delta_seconds):
        state["next_work"] = max(MIN_DURATION_SECONDS, state["next_work"] + delta_seconds)
        state["session_time_selected"] = True
        next_work_label.config(text=_format_timer(state["next_work"]))
        mins = int(round(state["next_work"] / 60))
        time_status_lbl.config(text=f"Duration: {_format_timer(state['next_work'])} (Custom ✓)", fg="#10B981")
        for m, btn in time_preset_buttons.items():
            if m == mins:
                btn.config(text=f"( ✓ {m}m )", bg="#06B6D4", fg="#020617", font=("Helvetica", 11, "bold"))
            else:
                btn.config(text=f"( {m}m )", bg="#1E293B", fg="#CBD5E1", font=("Helvetica", 11))
        state["interaction_log"].append({
            "event": "adjustNextWork",
            "deltaSeconds": delta_seconds,
            "at": int(time.time() - started_at),
            "nextWorkSeconds": state["next_work"],
        })
        update_resume_state()

    tk.Button(
        time_btn_frame,
        text="( -5m )",
        font=("Helvetica", 11, "bold"),
        bg="#7F1D1D",
        fg="#FCA5A5",
        activebackground="#991B1B",
        activeforeground="#FFFFFF",
        relief="flat",
        bd=0,
        cursor="hand2",
        padx=10,
        pady=5,
        command=lambda: adjust_next_work(-300),
    ).pack(side="left", padx=2)

    next_work_label = tk.Label(
        time_btn_frame,
        text=_format_timer(state["next_work"]),
        font=("Helvetica", 12, "bold"),
        fg="#FBBF24",
        bg="#0F172A",
        width=7,
    )
    next_work_label.pack(side="left", padx=3)

    tk.Button(
        time_btn_frame,
        text="( +5m )",
        font=("Helvetica", 11, "bold"),
        bg="#064E3B",
        fg="#6EE7B7",
        activebackground="#047857",
        activeforeground="#FFFFFF",
        relief="flat",
        bd=0,
        cursor="hand2",
        padx=10,
        pady=5,
        command=lambda: adjust_next_work(300),
    ).pack(side="left", padx=2)

    # SECTION 2: SINGLE FOCUS GOAL (STREAMLINED - ASK THE RIGHT QUESTION)
    row2 = tk.Frame(launchpad_card, bg="#0F172A")
    row2.pack(fill="x", pady=6)

    tk.Label(row2, text="🎯 PRIMARY FOCUS:", font=("Helvetica", 12, "bold"), fg="#94A3B8", bg="#0F172A", width=20, anchor="w").pack(side="left")

    act_status_lbl = tk.Label(
        row2,
        text="Focus: 💻 Deep Work / Code (✓)",
        font=("Helvetica", 11, "bold"),
        fg="#10B981",
        bg="#0F172A",
        width=34,
        anchor="e",
    )
    act_status_lbl.pack(side="right")

    act_btn_frame = tk.Frame(row2, bg="#0F172A")
    act_btn_frame.pack(side="left", padx=4)

    activity_options = [
        ("work", "💻 Deep Work / Code", "#2563EB"),
        ("study", "📚 Study & Learn", "#0284C7"),
        ("exercise", "🏋️ Exercise", "#059669"),
        ("other", "🎯 Focus Target", "#7C3AED"),
    ]
    activity_buttons = {}

    def update_activity_ui():
        for opt_key, opt_label, opt_glow in activity_options:
            btn = activity_buttons[opt_key]
            if opt_key in state["session_types"]:
                btn.config(
                    text=f"( ✓ {opt_label} )",
                    bg=opt_glow,
                    fg="#FFFFFF",
                    font=("Helvetica", 11, "bold"),
                )
            else:
                btn.config(
                    text=f"( {opt_label} )",
                    bg="#1E293B",
                    fg="#CBD5E1",
                    font=("Helvetica", 11),
                )

        selected_names = [opt_label for opt_key, opt_label, _ in activity_options if opt_key in state["session_types"]]
        if selected_names:
            act_status_lbl.config(
                text=f"{' + '.join(selected_names)} (✓)",
                fg="#10B981",
            )
        update_resume_state()

    def set_primary_activity(atype):
        state["session_types"] = {atype}
        state["session_type"] = atype
        state["interaction_log"].append({
            "event": "setSessionType",
            "type": atype,
            "at": int(time.time() - started_at),
        })
        update_activity_ui()

    for opt_key, opt_label, opt_glow in activity_options:
        btn = tk.Button(
            act_btn_frame,
            text=f"( {opt_label} )",
            font=("Helvetica", 11),
            bg="#1E293B",
            fg="#CBD5E1",
            activebackground=opt_glow,
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=14,
            pady=5,
            command=lambda k=opt_key: set_primary_activity(k),
        )
        btn.pack(side="left", padx=4)
        activity_buttons[opt_key] = btn

    update_activity_ui()

    # SECTION 3: FOCUS QUALITY RATING (CONFIRMED & INTUITIVE)
    row3 = tk.Frame(launchpad_card, bg="#0F172A")
    row3.pack(fill="x", pady=6)

    tk.Label(row3, text="⭐ FOCUS RATING:", font=("Helvetica", 12, "bold"), fg="#94A3B8", bg="#0F172A", width=20, anchor="w").pack(side="left")

    rating_status_lbl = tk.Label(
        row3,
        text="Rating: 4★ Great (Confirmed ✓)",
        font=("Helvetica", 11, "bold"),
        fg="#10B981",
        bg="#0F172A",
        width=34,
        anchor="e",
    )
    rating_status_lbl.pack(side="right")

    star_btn_frame = tk.Frame(row3, bg="#0F172A")
    star_btn_frame.pack(side="left", padx=4)

    rating_labels_map = {1: "1★ Low", 2: "2★ Fair", 3: "3★ Good", 4: "4★ Great", 5: "5★ Peak"}
    star_buttons = {}

    def select_rating(val):
        state["productivity_rating"] = val
        state["interaction_log"].append({"event": "setProductivity", "rating": val, "at": int(time.time() - started_at)})
        rating_status_lbl.config(text=f"Rating: {rating_labels_map[val]} (Confirmed ✓)", fg="#10B981")
        for r, btn in star_buttons.items():
            if r == val:
                btn.config(text=f"( ✓ {r}★ )", bg="#F59E0B", fg="#020617", font=("Helvetica", 11, "bold"))
            else:
                btn.config(text=f"( {r}★ )", bg="#1E293B", fg="#CBD5E1", font=("Helvetica", 11))
        update_resume_state()

    for r in range(1, 6):
        is_default_star = (r == 4)
        btn = tk.Button(
            star_btn_frame,
            text=f"( ✓ {r}★ )" if is_default_star else f"( {r}★ )",
            font=("Helvetica", 11, "bold" if is_default_star else "normal"),
            bg="#F59E0B" if is_default_star else "#1E293B",
            fg="#020617" if is_default_star else "#CBD5E1",
            activebackground="#F59E0B",
            activeforeground="#020617",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=16,
            pady=5,
            command=lambda val=r: select_rating(val),
        )
        btn.pack(side="left", padx=4)
        star_buttons[r] = btn

    update_resume_state()
    last_tick_at = time.time()

    while True:
        try:
            if not root.winfo_exists():
                break
        except Exception:
            break

        if (state["remaining"] <= 0 and (state["end_break_now"] or state["exit_app"])) or (state["remaining"] <= 0 and not state.get("break_completed_notified")) or state["end_break_now"] or state["exit_app"]:
            if state["remaining"] <= 0 and (state["end_break_now"] or state["exit_app"]):
                break
            if state["remaining"] <= 0 and not state.get("break_completed_notified"):
                state["break_completed_notified"] = True
                play_beep()
            if state["end_break_now"] or state["exit_app"]:
                break

        try:
            left, used = _get_skips_remaining(max_skips=MAX_DAILY_SKIPS)
            if state["remaining"] > 0:
                timer_label.config(text=_format_timer(state["remaining"]))
                timer_status_badge.config(text="🟢 BREAK TIMER RUNNING  •  STAND UP, STRETCH & RELAX YOUR EYES", fg="#10B981")
                if left <= 0:
                    skip_status_card.config(bg="#450A0A", highlightbackground="#EF4444")
                    skip_status_lbl.config(
                        text="🔒 DAILY SKIP LIMIT REACHED (2/2 USED) • SCREEN LOCKED UNTIL TIMER COMPLETES",
                        fg="#FCA5A5",
                        bg="#450A0A",
                    )
                    skip_limit_msg_lbl.config(bg="#450A0A")
                    if not skip_limit_msg_lbl.winfo_ismapped():
                        skip_limit_msg_lbl.pack(side="right")
                    resume_btn.config(
                        text="( 🔒 LOCKED: SKIP LIMIT REACHED (2/2) — YOU HAVE TO WAIT )",
                        bg="#1E293B",
                        fg="#EF4444",
                        state="disabled",
                        cursor="",
                    )
                else:
                    resume_btn.config(
                        text=f"( ⚡ RESUME WORK EARLY • {left}/2 Skips Left [Enter] )",
                        bg="#065F46",
                        fg="#A7F3D0",
                        state="normal",
                        cursor="hand2",
                    )
            else:
                timer_label.config(text="00:00 (Break Complete ✓)")
                timer_status_badge.config(text="🎉 4-MINUTE BREAK COMPLETE! Press [Enter] or click Resume to begin next focus session.", fg="#10B981")
                resume_btn.config(
                    text="( ⚡ RESUME NEXT WORK SESSION [Enter] • BREAK COMPLETE ✓ )",
                    bg="#10B981",
                    fg="#020617",
                    state="normal",
                    cursor="hand2",
                )
                if skip_limit_msg_lbl.winfo_ismapped():
                    skip_limit_msg_lbl.pack_forget()

            # Update live system performance in break header
            if get_system_metrics and state["remaining"] % 2 == 0:
                metrics = get_system_metrics()
                if metrics["is_high_usage"]:
                    sys_perf_lbl.config(
                        text=f"⚠️ HIGH USAGE: CPU {metrics['cpu_percent']:.0f}%  •  RAM {metrics['memory_percent']:.0f}% — Close heavy apps",
                        fg="#EF4444",
                        bg="#450A0A",
                        highlightbackground="#EF4444",
                    )
                else:
                    sys_perf_lbl.config(
                        text=f"💻 CPU: {metrics['cpu_percent']:.0f}%  |  RAM: {metrics['memory_percent']:.0f}% ({metrics['memory_used_gb']:.1f}/{metrics['memory_total_gb']:.1f} GB)  |  🌐 Net: {metrics['network_status']}",
                        fg="#94A3B8",
                        bg="#1E293B",
                        highlightbackground="#334155",
                    )

            root.update()
        except Exception:
            break

        if state["remaining"] <= 3:
            _play_countdown_alert(root)
        elif state["remaining"] <= 20 and not state["beep_20sec_played"]:
            state["beep_20sec_played"] = True
            play_beep()

        tick_before_sleep = time.time()
        time.sleep(1)
        tick_after_sleep = time.time()
        if _sleep_gap_detected(last_tick_at, tick_after_sleep):
            elapsed_gap = int(round(tick_after_sleep - last_tick_at))
            last_tick_at = tick_after_sleep
            state["active_elapsed_seconds"] += max(1, elapsed_gap)
            state["remaining"] = max(0, state["remaining"] - elapsed_gap)
            state["suspend_detected"] = False
            try:
                sw = root.winfo_screenwidth()
                sh = root.winfo_screenheight()
                root.geometry(f"{sw}x{sh}+0+0")
                root.attributes("-fullscreen", True)
                root.attributes("-topmost", True)
                root.lift()
                root.focus_force()
            except Exception:
                pass
            if state["remaining"] <= 0 and not state.get("break_completed_notified"):
                state["break_completed_notified"] = True
                play_beep()
        else:
            state["remaining"] -= 1
            state["active_elapsed_seconds"] += max(1, int(round(tick_after_sleep - tick_before_sleep)))
            last_tick_at = tick_after_sleep

    actual_break_seconds = state["active_elapsed_seconds"] or int(time.time() - started_at)
    if state["suspend_detected"]:
        ended_by = "systemSleep"
    elif state["exit_app"]:
        ended_by = "userExit"
    else:
        ended_by = "userEndBreakNow" if state["end_break_now"] else "timer"

    try:
        if root.winfo_exists():
            root.destroy()
    except Exception:
        pass

    selected_types_list = list(state["session_types"]) if state["session_types"] else ["work"]
    session_type_str = " + ".join(sorted(state["session_types"])) if state["session_types"] else "work"

    return {
        "plannedBreakSeconds": max(MIN_DURATION_SECONDS, int(break_seconds)),
        "actualBreakSeconds": max(1, actual_break_seconds),
        "breakEndedBy": ended_by,
        "exitApp": state.get("exit_app", False),
        "nextWorkSeconds": state["next_work"],
        "nextBreakSeconds": state["next_break"],
        "interactionLog": state["interaction_log"],
        "productivityRating": state.get("productivity_rating"),
        "routineSelected": state.get("routine_selected", "nothing"),
        "sessionTypes": selected_types_list,
        "sessionType": session_type_str,
        "activityType": session_type_str,
        "guiAvailable": True,
        "sessionInterruptedBySleep": state["suspend_detected"],
        "isWalkBreak": False,
    }
def lock_screen(break_time):
    result = run_break_session(
        break_seconds=break_time,
        default_next_work_seconds=40 * 60,
        default_next_break_seconds=4 * 60,
    )
    return result
