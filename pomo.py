import io
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image, ImageTk

os.environ["MPLCONFIGDIR"] = "/tmp"

MIN_DURATION_SECONDS = 60
SUSPEND_GAP_SECONDS = 10
_HEADLESS_WARNING_EMITTED = False


def _generate_break_dashboard_image(current_work_seconds=0, display_width=920, display_height=450):
    log_path = Path(__file__).resolve().parent / "pomodoro_log.json"
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
            "workEndedBy": "timer"
        }]

    if not events:
        return None

    df = pd.DataFrame(events)
    df["started_at"] = pd.to_datetime(df["sessionStartedAt"], errors="coerce")
    df["date"] = df["started_at"].dt.date
    df["work_hours"] = df["workTimeSeconds"].fillna(df.get("workTimeMinutes", 0) * 60) / 3600
    df["rating"] = pd.to_numeric(df.get("productivityRating", 0), errors="coerce").fillna(0)

    plt.style.use("dark_background")
    fig = plt.figure(figsize=(10, 5.2), facecolor="#0B0F19")
    fig.suptitle("POMODORO ANALYTICS & PRODUCTIVITY DASHBOARD", fontsize=13, fontweight="bold", color="#F3F4F6", y=0.97)

    # 1. Daily Work Hours Trend
    ax1 = fig.add_subplot(2, 2, 1, facecolor="#111827")
    daily_work = df.groupby("date")["work_hours"].sum().reset_index()
    daily_work["date"] = pd.to_datetime(daily_work["date"])
    daily_work = daily_work.sort_values("date")

    ax1.plot(daily_work["date"], daily_work["work_hours"], color="#38BDF8", linewidth=1.5)
    ax1.fill_between(daily_work["date"], daily_work["work_hours"], color="#38BDF8", alpha=0.2)
    ax1.set_title("Daily Focus Work Hours Over Time", fontsize=10, fontweight="bold", color="#E5E7EB", pad=6)
    ax1.set_ylabel("Hours", color="#9CA3AF", fontsize=8)
    ax1.grid(True, linestyle="--", alpha=0.15)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax1.tick_params(colors="#9CA3AF", labelsize=7)

    # 2. Rating Distribution
    ax2 = fig.add_subplot(2, 2, 2, facecolor="#111827")
    rating_counts = df[df["rating"] > 0]["rating"].value_counts().sort_index()
    if rating_counts.empty:
        rating_counts = pd.Series({3: 1})
    rating_labels = [f"{int(r)} Star" for r in rating_counts.index]
    colors = ["#EF4444", "#F59E0B", "#FBBF24", "#10B981", "#059669"]

    bars = ax2.bar(rating_labels, rating_counts.values, color=colors[:len(rating_counts)], width=0.45)
    ax2.set_title("Productivity Rating Distribution", fontsize=10, fontweight="bold", color="#E5E7EB", pad=6)
    ax2.set_ylabel("Session Count", color="#9CA3AF", fontsize=8)
    ax2.grid(axis="y", linestyle="--", alpha=0.15)
    ax2.tick_params(colors="#9CA3AF", labelsize=7)

    for bar in bars:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 1, f"{int(yval)}", ha="center", va="bottom", color="#F3F4F6", fontsize=7, fontweight="bold")

    # 3. Session End Reasons
    ax3 = fig.add_subplot(2, 2, 3, facecolor="#111827")
    end_reasons = df["workEndedBy"].value_counts()
    pie_colors = ["#6366F1", "#EC4899", "#8B5CF6", "#14B8A6", "#F59E0B"]

    wedges, texts, autotexts = ax3.pie(
        end_reasons.values,
        labels=end_reasons.index,
        colors=pie_colors[:len(end_reasons)],
        autopct="%1.1f%%",
        pctdistance=0.7,
        startangle=140,
        textprops=dict(color="#F3F4F6", fontsize=7, fontweight="bold")
    )
    centre_circle = plt.Circle((0, 0), 0.55, fc="#111827")
    ax3.add_artist(centre_circle)
    ax3.set_title("Work Session End Trigger Breakdown", fontsize=10, fontweight="bold", color="#E5E7EB", pad=6)

    # 4. Cumulative Focus Time Growth
    ax4 = fig.add_subplot(2, 2, 4, facecolor="#111827")
    daily_work["cumulative_hours"] = daily_work["work_hours"].cumsum()
    ax4.plot(daily_work["date"], daily_work["cumulative_hours"], color="#10B981", linewidth=1.8)
    ax4.fill_between(daily_work["date"], daily_work["cumulative_hours"], color="#10B981", alpha=0.2)
    ax4.set_title("Cumulative Focus Work Growth (Total Hours)", fontsize=10, fontweight="bold", color="#E5E7EB", pad=6)
    ax4.set_ylabel("Total Hours", color="#9CA3AF", fontsize=8)
    ax4.grid(True, linestyle="--", alpha=0.15)
    ax4.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax4.tick_params(colors="#9CA3AF", labelsize=7)

    total_hours = df["work_hours"].sum()
    total_sessions = len(df)
    top_day_hours = daily_work["work_hours"].max()
    top_day_date = daily_work.loc[daily_work["work_hours"].idxmax()]["date"].strftime("%b %d, %Y")
    avg_rating = df[df["rating"] > 0]["rating"].mean() if not df[df["rating"] > 0].empty else 3.0

    stats_text = f"TOTAL: {total_hours:.1f} hrs  |  SESSIONS: {total_sessions}  |  TOP DAY: {top_day_hours:.1f} hrs ({top_day_date})  |  AVG RATING: {avg_rating:.1f}/5"
    fig.text(0.5, 0.02, stats_text, ha="center", fontsize=9, fontweight="bold", color="#38BDF8", bbox=dict(boxstyle="round,pad=0.3", facecolor="#111827", edgecolor="#374151"))

    plt.tight_layout(rect=[0, 0.04, 1, 0.94])

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    img = Image.open(buf)
    img = img.resize((display_width, display_height), Image.Resampling.LANCZOS)
    return img



def _load_summary_stats(current_work_seconds=0):
    log_path = Path(__file__).resolve().parent / "pomodoro_log.json"
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

    return {
        "today_sessions": today_sessions,
        "today_work": format_duration(today_work_sec),
        "today_break": format_duration(today_break_sec),
        "today_rating": today_avg,
        "total_sessions": total_sessions,
        "total_work": format_duration(total_work_sec),
        "total_rating": total_avg,
        "top_day": top_day_str,
        "timer_pct": f"{timer_pct}%",
        "sleep_pct": f"{sleep_pct}%",
    }


def _render_text_stats_card(container, stats_data=None):
    import tkinter as tk
    if stats_data is None:
        stats_data = _load_summary_stats()

    stats_title_row = tk.Frame(container, bg="#111827")
    stats_title_row.pack(fill="x", pady=(0, 6))

    tk.Label(
        stats_title_row,
        text="⚡ LIVE ANALYTICS DASHBOARD",
        font=("Helvetica", 11, "bold"),
        fg="#F3F4F6",
        bg="#111827",
    ).pack(side="left")

    grid_frame = tk.Frame(container, bg="#111827")
    grid_frame.pack(fill="x")
    grid_frame.columnconfigure(0, weight=1)
    grid_frame.columnconfigure(1, weight=1)

    col1 = tk.Frame(grid_frame, bg="#1E293B", padx=12, pady=10, highlightbackground="#334155", highlightthickness=1)
    col1.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    tk.Label(col1, text="📅 TODAY'S PERFORMANCE", font=("Helvetica", 10, "bold"), fg="#38BDF8", bg="#1E293B").pack(anchor="w", pady=(0, 4))
    tk.Label(col1, text=f"Sessions Completed:  {stats_data['today_sessions']}", font=("Helvetica", 11, "bold"), fg="#F9FAFB", bg="#1E293B").pack(anchor="w", pady=1)
    tk.Label(col1, text=f"Total Work Time:    {stats_data['today_work']}   |   Break: {stats_data['today_break']}", font=("Helvetica", 10), fg="#CBD5E1", bg="#1E293B").pack(anchor="w", pady=1)

    col2 = tk.Frame(grid_frame, bg="#1E293B", padx=12, pady=10, highlightbackground="#334155", highlightthickness=1)
    col2.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    tk.Label(col2, text="🚀 ALL-TIME CAREER METRICS", font=("Helvetica", 10, "bold"), fg="#10B981", bg="#1E293B").pack(anchor="w", pady=(0, 4))
    tk.Label(col2, text=f"Total Focus Time:   {stats_data['total_work']}  ({stats_data['total_sessions']} Sessions)", font=("Helvetica", 11, "bold"), fg="#F9FAFB", bg="#1E293B").pack(anchor="w", pady=1)
    tk.Label(col2, text=f"Top Output Day:     {stats_data.get('top_day', 'N/A')}", font=("Helvetica", 10), fg="#F59E0B", bg="#1E293B").pack(anchor="w", pady=1)



def _warn_headless_once(error):
    global _HEADLESS_WARNING_EMITTED
    if _HEADLESS_WARNING_EMITTED:
        return

    _HEADLESS_WARNING_EMITTED = True
    print(f"GUI unavailable ({error}); running headless.")
    if not os.environ.get("DISPLAY"):
        print(
            "Hint: set DISPLAY/XAUTHORITY for pomodoro.service (or import env in systemd --user)."
        )


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
    sound_files = [
        "/usr/share/sounds/freedesktop/stereo/bell.oga",
        "/usr/share/sounds/freedesktop/stereo/message.oga",
        "/usr/share/sounds/oxygen/stereo/dialog-information.ogg",
        "/usr/share/sounds/Oxygen-Sys-Special.ogg",
        "/usr/share/sounds/alsa/Front_Center.wav",
    ]
    
    # Try pw-play, paplay, aplay in background
    for player in ["pw-play", "paplay", "aplay"]:
        for sound_file in sound_files:
            if Path(sound_file).exists():
                try:
                    subprocess.Popen([player, sound_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
                except Exception:
                    pass
                    
    # Fallback to spd-say
    try:
        subprocess.Popen(["spd-say", "-t", "female1", "beep"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        pass

    # Fallback to tkinter bell/terminal beep in background thread
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
            print(
                f"Display unavailable ({error}); retrying in {retry_delay}s until display is ready."
            )
            time.sleep(retry_delay)


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

    # keep the work session out of the way: do not make it topmost or foreground
    root.attributes("-topmost", False)
    root.geometry("720x420")
    root.iconify()
    root.configure(bg="#111827")

    started_at = time.time()
    last_tick_at = started_at
    state = {
        "remaining": max(MIN_DURATION_SECONDS, int(work_seconds)),
        "go_break_now": False,
        "interaction_log": [],
        "suspend_detected": False,
        "active_elapsed_seconds": 0,
        "beep_1min_played": False,
    }

    title_label = tk.Label(
        root,
        text="Work Session",
        font=("Helvetica", 28, "bold"),
        fg="#F9FAFB",
        bg="#111827",
    )
    title_label.pack(pady=20)

    timer_label = tk.Label(
        root,
        text=_format_timer(state["remaining"]),
        font=("Helvetica", 72, "bold"),
        fg="#34D399",
        bg="#111827",
    )
    timer_label.pack(pady=20)

    message_label = tk.Label(
        root,
        text="Stay focused. You can jump to break when needed.",
        font=("Helvetica", 14),
        fg="#D1D5DB",
        bg="#111827",
    )
    message_label.pack(pady=10)

    def go_on_break_now():
        if state["go_break_now"]:
            return
        state["go_break_now"] = True
        state["interaction_log"].append(
            {"event": "goBreakNow", "at": int(time.time() - started_at)}
        )

    action_button = tk.Button(
        root,
        text="Go On Break Now",
        font=("Helvetica", 16, "bold"),
        bg="#F59E0B",
        fg="#111827",
        padx=16,
        pady=10,
        command=go_on_break_now,
    )
    action_button.pack(pady=24)

    while state["remaining"] > 0 and not state["go_break_now"]:
        timer_label.config(text=_format_timer(state["remaining"]))
        root.update()
        if state["remaining"] <= 3:
            _play_countdown_alert(root)
        elif state["remaining"] <= 60 and not state["beep_1min_played"]:
            state["beep_1min_played"] = True
            play_beep()
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

    root.destroy()

    return {
        "plannedWorkSeconds": max(MIN_DURATION_SECONDS, int(work_seconds)),
        "actualWorkSeconds": max(1, actual_work_seconds),
        "workEndedBy": ended_by,
        "interactionLog": state["interaction_log"],
        "guiAvailable": True,
        "sessionInterruptedBySleep": state["suspend_detected"],
    }


def run_break_session(
    break_seconds,
    default_next_work_seconds,
    default_next_break_seconds,
    stats=None,
):
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
            "exitApp": False,
            "sessionCanceled": True,
            "guiAvailable": False,
        }
    import tkinter as tk

    # make the break session full screen and remove window decorations
    root.update_idletasks()
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
    # remove window manager decorations so user cannot minimize/close
    try:
        root.overrideredirect(True)
    except Exception:
        pass
    root.configure(bg="#030712")
    # Try to make the break window always on top and capture input so other
    # applications cannot be brought forward while the break is active.
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass
    try:
        root.lift()
        root.focus_force()
    except Exception:
        pass
    # Try to grab all input (best-effort; some window managers may prevent this)
    try:
        root.grab_set_global()
    except Exception:
        try:
            root.grab_set()
        except Exception:
            pass
    # If focus is lost, immediately re-focus the break window
    try:
        def _on_focus_out(event):
            try:
                root.lift()
                root.focus_force()
            except Exception:
                pass

        root.bind("<FocusOut>", _on_focus_out)
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
        "productivity_rating": None,
        "suspend_detected": False,
        "active_elapsed_seconds": 0,
        "beep_20sec_played": False,
    }

    # Central container for all break UI elements
    main_frame = tk.Frame(root, bg="#090D16")
    main_frame.pack(expand=True, fill="both", padx=30, pady=20)

    # Top Header
    header_frame = tk.Frame(main_frame, bg="#090D16")
    header_frame.pack(pady=(10, 4))

    tk.Label(
        header_frame,
        text="☕ REST & RECHARGE",
        font=("Helvetica", 24, "bold"),
        fg="#38BDF8",
        bg="#090D16",
    ).pack()

    tk.Label(
        header_frame,
        text="Enforced Focus Break • Stand up, stretch & take a deep breath",
        font=("Helvetica", 11),
        fg="#9CA3AF",
        bg="#090D16",
    ).pack(pady=(2, 0))

    # Giant Countdown Timer
    timer_label = tk.Label(
        main_frame,
        text=_format_timer(state["remaining"]),
        font=("Helvetica", 84, "bold"),
        fg="#60A5FA",
        bg="#090D16",
    )
    timer_label.pack(pady=(4, 10))

    # 📊 FULL GRAPHICAL ANALYTICS DASHBOARD CONTAINER
    stats_container = tk.Frame(
        main_frame,
        bg="#0B0F19",
        highlightbackground="#1F2937",
        highlightthickness=1,
        padx=4,
        pady=4,
    )
    stats_container.pack(pady=(0, 10), fill="both", expand=True)

    sw = 1280
    sh = 800
    try:
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
    except Exception:
        pass

    target_w = max(600, min(1020, sw - 140))
    target_h = max(300, min(480, int(sh * 0.46)))

    try:
        raw_dash_img = _generate_break_dashboard_image(
            current_work_seconds=0,
            display_width=target_w,
            display_height=target_h
        )
        if raw_dash_img:
            state["dashboard_photo"] = ImageTk.PhotoImage(raw_dash_img)
            dash_img_lbl = tk.Label(stats_container, image=state["dashboard_photo"], bg="#0B0F19")
            dash_img_lbl.pack(expand=True)
        else:
            _render_text_stats_card(stats_container, stats)
    except Exception as img_err:
        print(f"Fallback to text stats due to chart render error: {img_err}")
        _render_text_stats_card(stats_container, stats)

    # 🎛️ CONTROLS CONTAINER (Break duration & Next Work duration)
    controls_frame = tk.Frame(main_frame, bg="#111827", highlightbackground="#1F2937", highlightthickness=1, padx=16, pady=10)
    controls_frame.pack(fill="x", pady=(0, 12))

    ctrl_grid = tk.Frame(controls_frame, bg="#111827")
    ctrl_grid.pack(expand=True)

    # Break duration row
    tk.Label(ctrl_grid, text="Break Length:", font=("Helvetica", 11, "bold"), fg="#93C5FD", bg="#111827").grid(row=0, column=0, padx=8, pady=4, sticky="e")
    
    def update_break_duration(delta_seconds):
        state["remaining"] = max(MIN_DURATION_SECONDS, state["remaining"] + delta_seconds)
        if state["remaining"] > 20:
            state["beep_20sec_played"] = False
        break_length_label.config(text=_format_timer(state["remaining"]))
        state["interaction_log"].append(
            {
                "event": "adjustCurrentBreak",
                "deltaSeconds": delta_seconds,
                "at": int(time.time() - started_at),
                "newCurrentBreakSeconds": state["remaining"],
            }
        )

    tk.Button(ctrl_grid, text="-1 min", font=("Helvetica", 10, "bold"), bg="#DC2626", fg="#F9FAFB", activebackground="#EF4444", padx=8, pady=2, command=lambda: update_break_duration(-60)).grid(row=0, column=1, padx=4)
    break_length_label = tk.Label(ctrl_grid, text=_format_timer(state["remaining"]), font=("Helvetica", 14, "bold"), fg="#60A5FA", bg="#111827", width=6)
    break_length_label.grid(row=0, column=2, padx=4)
    tk.Button(ctrl_grid, text="+1 min", font=("Helvetica", 10, "bold"), bg="#059669", fg="#F9FAFB", activebackground="#10B981", padx=8, pady=2, command=lambda: update_break_duration(60)).grid(row=0, column=3, padx=4)

    # Divider
    tk.Label(ctrl_grid, text="   |   ", font=("Helvetica", 12), fg="#475569", bg="#111827").grid(row=0, column=4, padx=6)

    # Next Work row
    tk.Label(ctrl_grid, text="Next Work:", font=("Helvetica", 11, "bold"), fg="#FDE68A", bg="#111827").grid(row=0, column=5, padx=8, pady=4, sticky="e")

    def update_next_work(delta_seconds):
        state["next_work"] = max(MIN_DURATION_SECONDS, state["next_work"] + delta_seconds)
        next_work_label.config(text=_format_timer(state["next_work"]))
        state["interaction_log"].append(
            {
                "event": "adjustNextWork",
                "deltaSeconds": delta_seconds,
                "at": int(time.time() - started_at),
                "nextWorkSeconds": state["next_work"],
            }
        )

    tk.Button(ctrl_grid, text="-5 min", font=("Helvetica", 10, "bold"), bg="#B91C1C", fg="#F9FAFB", activebackground="#DC2626", padx=8, pady=2, command=lambda: update_next_work(-300)).grid(row=0, column=6, padx=4)
    next_work_label = tk.Label(ctrl_grid, text=_format_timer(state["next_work"]), font=("Helvetica", 14, "bold"), fg="#FBBF24", bg="#111827", width=6)
    next_work_label.grid(row=0, column=7, padx=4)
    tk.Button(ctrl_grid, text="+5 min", font=("Helvetica", 10, "bold"), bg="#047857", fg="#F9FAFB", activebackground="#059669", padx=8, pady=2, command=lambda: update_next_work(300)).grid(row=0, column=8, padx=4)

    # ⭐ PRODUCTIVITY RATING SECTION
    rating_frame = tk.Frame(main_frame, bg="#111827", highlightbackground="#1F2937", highlightthickness=1, padx=16, pady=10)
    rating_frame.pack(fill="x", pady=(0, 14))

    rating_top_row = tk.Frame(rating_frame, bg="#111827")
    rating_top_row.pack(fill="x", pady=(0, 6))

    tk.Label(rating_top_row, text="⭐ RATE THIS SESSION'S FOCUS LEVEL", font=("Helvetica", 10, "bold"), fg="#F3F4F6", bg="#111827").pack(side="left")
    rating_status_lbl = tk.Label(rating_top_row, text="Rating: 3 ★ (Good)", font=("Helvetica", 10, "bold"), fg="#FBBF24", bg="#111827")
    rating_status_lbl.pack(side="right")

    star_btn_frame = tk.Frame(rating_frame, bg="#111827")
    star_btn_frame.pack(expand=True)

    rating_labels_map = {1: "1 ★ Low", 2: "2 ★ Fair", 3: "3 ★ Good", 4: "4 ★ Great", 5: "5 ★ Peak Focus"}
    star_buttons = {}

    def select_rating(val):
        state["productivity_rating"] = val
        state["interaction_log"].append(
            {"event": "setProductivity", "rating": val, "at": int(time.time() - started_at)}
        )
        rating_status_lbl.config(text=f"Rating: {rating_labels_map[val]}")
        for r, btn in star_buttons.items():
            if r == val:
                btn.config(bg="#F59E0B", fg="#090D16", font=("Helvetica", 10, "bold"))
            else:
                btn.config(bg="#1E293B", fg="#94A3B8", font=("Helvetica", 10))

    for r in range(1, 6):
        btn = tk.Button(
            star_btn_frame,
            text=f"{r} ★",
            font=("Helvetica", 10, "bold" if r == 3 else "normal"),
            bg="#F59E0B" if r == 3 else "#1E293B",
            fg="#090D16" if r == 3 else "#94A3B8",
            padx=16,
            pady=4,
            command=lambda val=r: select_rating(val),
        )
        btn.pack(side="left", padx=4)
        star_buttons[r] = btn

    state["productivity_rating"] = 3

    # 🚀 ACTION FOOTER BUTTONS
    footer_frame = tk.Frame(main_frame, bg="#090D16")
    footer_frame.pack(pady=4)

    def end_break_now():
        if state["end_break_now"]:
            return
        state["end_break_now"] = True
        state["interaction_log"].append(
            {"event": "endBreakNow", "at": int(time.time() - started_at)}
        )

    def exit_app():
        if state["exit_app"]:
            return
        state["exit_app"] = True
        state["interaction_log"].append(
            {"event": "exitApp", "at": int(time.time() - started_at)}
        )

    resume_btn = tk.Button(
        footer_frame,
        text="⚡ RESUME WORK NOW",
        font=("Helvetica", 14, "bold"),
        bg="#F59E0B",
        fg="#090D16",
        activebackground="#FBBF24",
        activeforeground="#090D16",
        padx=28,
        pady=8,
        command=end_break_now,
    )
    resume_btn.pack(side="left", padx=10)

    exit_btn = tk.Button(
        footer_frame,
        text="🔴 EXIT APP",
        font=("Helvetica", 11, "bold"),
        bg="#991B1B",
        fg="#F9FAFB",
        activebackground="#DC2626",
        padx=16,
        pady=8,
        command=exit_app,
    )
    exit_btn.pack(side="left", padx=10)

    while state["remaining"] > 0 and not state["end_break_now"] and not state["exit_app"]:
        timer_label.config(text=_format_timer(state["remaining"]))
        break_length_label.config(text=_format_timer(state["remaining"]))
        root.update()
        if state["remaining"] <= 3:
            _play_countdown_alert(root)
        elif state["remaining"] <= 20 and not state["beep_20sec_played"]:
            state["beep_20sec_played"] = True
            play_beep()
        tick_before_sleep = time.time()
        time.sleep(1)
        tick_after_sleep = time.time()
        if _sleep_gap_detected(last_tick_at, tick_after_sleep):
            state["suspend_detected"] = True
            break

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

    root.destroy()

    return {
        "plannedBreakSeconds": max(MIN_DURATION_SECONDS, int(break_seconds)),
        "actualBreakSeconds": max(1, actual_break_seconds),
        "breakEndedBy": ended_by,
        "exitApp": state.get("exit_app", False),
        "nextWorkSeconds": state["next_work"],
        "nextBreakSeconds": state["next_break"],
        "interactionLog": state["interaction_log"],
        "productivityRating": state.get("productivity_rating"),
        "guiAvailable": True,
        "sessionInterruptedBySleep": state["suspend_detected"],
    }


def lock_screen(break_time):
    result = run_break_session(
        break_seconds=break_time,
        default_next_work_seconds=40 * 60,
        default_next_break_seconds=4 * 60,
    )
    return result
