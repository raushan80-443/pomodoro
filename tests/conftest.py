import os
import sys
import tempfile
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture(autouse=True)
def isolated_log_environment(tmp_path, monkeypatch):
    """
    Ensures that every test runs with an isolated temporary pomodoro_log.json,
    leaving production data completely untouched.
    """
    temp_log_file = tmp_path / "pomodoro_test_log.json"
    monkeypatch.setenv("POMODORO_LOG_PATH", str(temp_log_file))
    yield temp_log_file
    if temp_log_file.exists():
        try:
            temp_log_file.unlink()
        except Exception:
            pass
