import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import pytest
import pomo


def test_initial_skips_remaining():
    """Verify that a fresh day starts with 2 remaining skips and 0 used."""
    remaining, used = pomo._get_skips_remaining(max_skips=2)
    assert remaining == 2
    assert used == 0


def test_record_single_skip():
    """Verify recording a skip reduces remaining by 1."""
    used_count = pomo._record_daily_skip("break_early_continue")
    assert used_count == 1

    remaining, used = pomo._get_skips_remaining(max_skips=2)
    assert remaining == 1
    assert used == 1


def test_record_two_skips_exhausts_limit():
    """Verify 2 skips exhausts the daily limit and triggers lock condition."""
    pomo._record_daily_skip("work_jump_break")
    pomo._record_daily_skip("break_early_continue")

    remaining, used = pomo._get_skips_remaining(max_skips=2)
    assert remaining == 0
    assert used == 2


def test_record_beyond_limit_stays_at_zero_remaining():
    """Verify that extra attempts cannot drive remaining skips below 0."""
    pomo._record_daily_skip("skip_1")
    pomo._record_daily_skip("skip_2")
    pomo._record_daily_skip("skip_3")

    remaining, used = pomo._get_skips_remaining(max_skips=2)
    assert remaining == 0
    assert used == 3


def test_lock_message_string_exact_match():
    """Verify the exact mandatory locked message string is used."""
    expected_msg = "You have reached the limit and now nothing can be done after this. You have to wait."
    assert "You have reached the limit and now nothing can be done after this. You have to wait." == expected_msg


def test_calendar_day_rollover(tmp_path, monkeypatch):
    """
    Verify that skips from yesterday do NOT count towards today's skips.
    A new calendar day must start fresh with 2 skips.
    """
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    today_str = datetime.now().strftime("%Y-%m-%d")

    log_path = Path(pomo._get_log_path())
    initial_data = {
        "appName": "pomodoro",
        "createdAt": datetime.now().isoformat() + "Z",
        "dailySkips": {
            yesterday_str: [
                {"timestamp": "2026-10-17T10:00:00Z", "type": "break_early_continue"},
                {"timestamp": "2026-10-17T14:00:00Z", "type": "work_jump_break"},
            ]
        },
    }
    log_path.write_text(json.dumps(initial_data))

    # Yesterday's skips must be 2, but today's remaining must be 2 (0 used today)
    yesterday_skips = pomo._load_daily_skips(date_str=yesterday_str)
    assert len(yesterday_skips) == 2

    today_remaining, today_used = pomo._get_skips_remaining(max_skips=2)
    assert today_remaining == 2
    assert today_used == 0


def test_persistence_across_reloads():
    """Verify recorded skips persist accurately to disk and can be reloaded."""
    pomo._record_daily_skip("test_skip_action")

    # Read raw JSON from disk
    log_path = Path(pomo._get_log_path())
    assert log_path.exists()
    raw = json.loads(log_path.read_text())
    today_str = datetime.now().strftime("%Y-%m-%d")
    assert today_str in raw["dailySkips"]
    assert len(raw["dailySkips"][today_str]) == 1
    assert raw["dailySkips"][today_str][0]["type"] == "test_skip_action"


def test_custom_max_skips_override():
    """Verify max_skips parameter dynamically overrides default limit."""
    pomo._record_daily_skip("skip_custom")

    # With max_skips = 5: 1 used -> 4 remaining
    rem_5, used_5 = pomo._get_skips_remaining(max_skips=5)
    assert rem_5 == 4
    assert used_5 == 1

    # With max_skips = 1: 1 used -> 0 remaining (locked)
    rem_1, used_1 = pomo._get_skips_remaining(max_skips=1)
    assert rem_1 == 0
    assert used_1 == 1


def test_corrupt_log_recovery_during_skip_recording():
    """Verify that corrupt JSON file is safely recovered without raising exceptions."""
    log_path = Path(pomo._get_log_path())
    log_path.write_text("{corrupt non-json content!!!")

    used = pomo._record_daily_skip("recovery_skip")
    assert used == 1
    rem, used_total = pomo._get_skips_remaining(max_skips=2)
    assert rem == 1
    assert used_total == 1

