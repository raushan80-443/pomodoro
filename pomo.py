import os
import subprocess
import time
from pathlib import Path


MIN_DURATION_SECONDS = 60
SUSPEND_GAP_SECONDS = 10
_HEADLESS_WARNING_EMITTED = False


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


def run_break_session(break_seconds, default_next_work_seconds, default_next_break_seconds):
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
    main_frame = tk.Frame(root, bg="#030712")
    main_frame.pack(expand=True)

    title_label = tk.Label(
        main_frame,
        text="Break Time",
        font=("Helvetica", 30, "bold"),
        fg="#F9FAFB",
        bg="#030712",
    )
    title_label.pack(pady=16)

    timer_label = tk.Label(
        main_frame,
        text=_format_timer(state["remaining"]),
        font=("Helvetica", 78, "bold"),
        fg="#60A5FA",
        bg="#030712",
    )
    timer_label.pack(pady=10)

    current_break_label = tk.Label(
        main_frame,
        text="Current Break Length",
        font=("Helvetica", 14, "bold"),
        fg="#E5E7EB",
        bg="#030712",
    )
    current_break_label.pack(pady=(18, 8))

    control_row = tk.Frame(main_frame, bg="#030712")
    control_row.pack(pady=8)

    break_length_label = tk.Label(
        control_row,
        text=_format_timer(state["remaining"]),
        font=("Helvetica", 18, "bold"),
        fg="#93C5FD",
        bg="#030712",
        width=8,
    )

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

    tk.Button(
        control_row,
        text="-1 min",
        font=("Helvetica", 12, "bold"),
        bg="#EF4444",
        fg="#F9FAFB",
        padx=10,
        command=lambda: update_break_duration(-60),
    ).pack(side="left", padx=6)

    break_length_label.pack(side="left", padx=8)

    tk.Button(
        control_row,
        text="+1 min",
        font=("Helvetica", 12, "bold"),
        bg="#10B981",
        fg="#F9FAFB",
        padx=10,
        command=lambda: update_break_duration(60),
    ).pack(side="left", padx=6)

    next_row = tk.Frame(main_frame, bg="#030712")
    next_row.pack(pady=24)

    next_work_label = tk.Label(
        next_row,
        text=f"Next Work: {_format_timer(state['next_work'])}",
        font=("Helvetica", 14, "bold"),
        fg="#FDE68A",
        bg="#030712",
    )
    next_work_label.grid(row=0, column=0, padx=12, pady=8)
    def update_next_work(delta_seconds):
        state["next_work"] = max(MIN_DURATION_SECONDS, state["next_work"] + delta_seconds)
        next_work_label.config(text=f"Next Work: {_format_timer(state['next_work'])}")
        state["interaction_log"].append(
            {
                "event": "adjustNextWork",
                "deltaSeconds": delta_seconds,
                "at": int(time.time() - started_at),
                "nextWorkSeconds": state["next_work"],
            }
        )

    tk.Button(
        next_row,
        text="Work -5 min",
        font=("Helvetica", 11, "bold"),
        bg="#DC2626",
        fg="#F9FAFB",
        command=lambda: update_next_work(-300),
    ).grid(row=0, column=1, padx=6)

    tk.Button(
        next_row,
        text="Work +5 min",
        font=("Helvetica", 11, "bold"),
        bg="#059669",
        fg="#F9FAFB",
        command=lambda: update_next_work(300),
    ).grid(row=0, column=2, padx=6)

    # Productivity rating: 1 (non-productive) .. 5 (productive)
    rating_label = tk.Label(
        main_frame,
        text="Rate this break (1 = non-productive, 5 = productive)",
        font=("Helvetica", 14, "bold"),
        fg="#E5E7EB",
        bg="#030712",
    )
    rating_label.pack(pady=(12, 6))

    def _on_rating_change(val):
        try:
            rating = int(float(val))
        except Exception:
            return
        state["productivity_rating"] = rating
        state["interaction_log"].append(
            {"event": "setProductivity", "rating": rating, "at": int(time.time() - started_at)}
        )

    rating_scale = tk.Scale(
        main_frame,
        from_=1,
        to=5,
        orient="horizontal",
        length=320,
        bg="#030712",
        fg="#F9FAFB",
        troughcolor="#1E293B",
        showvalue=True,
        resolution=1,
        command=_on_rating_change,
    )
    # default to neutral 3 so sessions always have a rating when GUI used
    rating_scale.set(3)
    state["productivity_rating"] = 3
    rating_scale.pack(pady=(0, 12))

    # removed 'Next Break' and related disabled control per user request

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

    tk.Button(
        main_frame,
        text="End Break Now",
        font=("Helvetica", 16, "bold"),
        bg="#F59E0B",
        fg="#111827",
        padx=18,
        pady=10,
        command=end_break_now,
    ).pack(pady=18)

    # Exit button (terminates the program after saving) — centered
    exit_btn = tk.Button(
        main_frame,
        text="Exit",
        font=("Helvetica", 12, "bold"),
        bg="#EF4444",
        fg="#F9FAFB",
        padx=12,
        pady=6,
        command=exit_app,
    )
    exit_btn.pack()

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
