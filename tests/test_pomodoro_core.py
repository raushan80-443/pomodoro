import os
from datetime import datetime
import pytest
import pomo


def test_warning_seconds_default_is_two_minutes():
    """Verify that the pre-break warning timer is configured to 120 seconds (2 minutes)."""
    assert pomo.WARNING_SECONDS == 120


def test_routine_completions_lifecycle():
    """Verify routine tasks can be marked complete, retrieved, and are idempotent."""
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Initial state should be empty
    initial = pomo._load_routine_completions()
    assert initial == []

    # Save a completion
    pomo._save_routine_completion("exercise", "Morning Workout")
    completions = pomo._load_routine_completions()
    assert len(completions) == 1
    assert completions[0]["taskId"] == "exercise"
    assert completions[0]["date"] == today_str

    # Saving the same completion again on the same day must not duplicate
    pomo._save_routine_completion("exercise", "Morning Workout")
    completions_repeat = pomo._load_routine_completions()
    assert len(completions_repeat) == 1

    # Saving a different task adds to the list
    pomo._save_routine_completion("water_am", "Drink Water")
    completions_both = pomo._load_routine_completions()
    assert len(completions_both) == 2


def test_load_summary_stats_empty():
    """Verify summary stats load safely even when no previous events exist."""
    stats_zero = pomo._load_summary_stats(current_work_seconds=0)
    assert isinstance(stats_zero, dict)
    assert stats_zero["today_sessions"] == 0
    assert stats_zero["today_work"] == "0m"
    assert stats_zero["total_sessions"] == 0

    stats_in_progress = pomo._load_summary_stats(current_work_seconds=1200)
    assert stats_in_progress["today_sessions"] == 1
    assert stats_in_progress["today_work"] == "20m"


def test_time_slot_resolution():
    """Verify _get_time_slot returns a valid known slot (morning, afternoon, evening)."""
    slot = pomo._get_time_slot()
    assert slot in {"morning", "afternoon", "evening"}


def test_routine_schedule_structure():
    """Verify DEFAULT_ROUTINE_SCHEDULE contains tasks for morning, afternoon, evening."""
    schedule = pomo.DEFAULT_ROUTINE_SCHEDULE
    for slot in ["morning", "afternoon", "evening"]:
        assert slot in schedule
        assert "tasks" in schedule[slot]
        assert len(schedule[slot]["tasks"]) > 0
        for task in schedule[slot]["tasks"]:
            assert "id" in task
            assert "title" in task


def test_run_break_session_initialization(monkeypatch):
    """Verify run_break_session initializes cleanly without NameError (e.g. resume_btn unbound error)."""
    orig_create = pomo._create_tk_root

    def auto_close_root(*args, **kwargs):
        root = orig_create(*args, **kwargs)
        # Schedule auto destroy after 20ms to allow full initialization
        root.after(20, lambda: root.destroy() if root.winfo_exists() else None)
        return root

    monkeypatch.setattr(pomo, "_create_tk_root", auto_close_root)

    result = pomo.run_break_session(
        break_seconds=240,
        default_next_work_seconds=2400,
        default_next_break_seconds=240,
        stats={"today_sessions": 1, "streak_days": "1 Day 🔥"},
        is_walk_break=False,
        session_number=1,
    )
    assert result["plannedBreakSeconds"] == 240
    assert result["guiAvailable"] is True


def test_run_work_session_when_skips_exhausted(monkeypatch):
    """Verify run_work_session initializes cleanly without TclError when daily skips are exhausted."""
    orig_create = pomo._create_tk_root

    def auto_close_root(*args, **kwargs):
        root = orig_create(*args, **kwargs)
        root.after(20, lambda: root.destroy() if root.winfo_exists() else None)
        return root

    monkeypatch.setattr(pomo, "_create_tk_root", auto_close_root)
    monkeypatch.setattr(pomo, "_get_skips_remaining", lambda max_skips=None: (0, 2))

    result = pomo.run_work_session(work_seconds=60)
    assert result["plannedWorkSeconds"] == 60
    assert result["guiAvailable"] is True


def test_run_break_session_when_skips_exhausted(monkeypatch):
    """Verify run_break_session initializes cleanly without TclError when daily skips are exhausted."""
    orig_create = pomo._create_tk_root

    def auto_close_root(*args, **kwargs):
        root = orig_create(*args, **kwargs)
        root.after(20, lambda: root.destroy() if root.winfo_exists() else None)
        return root

    monkeypatch.setattr(pomo, "_create_tk_root", auto_close_root)
    monkeypatch.setattr(pomo, "_get_skips_remaining", lambda max_skips=None: (0, 2))

    result = pomo.run_break_session(
        break_seconds=240,
        default_next_work_seconds=2400,
        default_next_break_seconds=240,
        stats={"today_sessions": 1, "streak_days": "1 Day 🔥"},
        is_walk_break=False,
        session_number=1,
    )
    assert result["plannedBreakSeconds"] == 240
    assert result["guiAvailable"] is True
